"""
RAG (Retrieval Augmented Generation) module for medical board items.
Provides semantic search over patient data, lab results, medications, and clinical notes.
"""

import json
import os
import pickle
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai.types import EmbedContentConfig
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import canvas_ops
import time

load_dotenv()

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_LOCATION = os.getenv("PROJECT_LOCATION", "us-central1")
EMBEDDING_MODEL = "text-embedding-005"
EMBEDDING_DIM = 768
INDEX_CACHE_PATH = "vector_cache/rag_index.pkl"

# Initialize client
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=PROJECT_LOCATION,
)


def load_board_items(file_path: str = "output/board_items.json") -> List[Dict[str, Any]]:
    """Load board items from Canvas Ops or fallback to JSON file."""
    try:
        items = canvas_ops.get_board_items()
        if items:
            return items
        # Fallback if canvas_ops returns empty
        print("Canvas returned empty, falling back to file.")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading board items: {e}")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []


def compute_item_hash(item: Dict[str, Any]) -> str:
    """Compute hash of item content to detect changes."""
    # Create a stable string representation of the item
    # We only care about content fields, not ephemeral UI states if possible
    item_str = json.dumps(item, sort_keys=True)
    return hashlib.md5(item_str.encode()).hexdigest()


def save_index(index_df: pd.DataFrame, file_path: str = INDEX_CACHE_PATH) -> None:
    """Save index to disk."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        pickle.dump(index_df, f)
    print(f"Index saved to {file_path}")


def load_index(file_path: str = INDEX_CACHE_PATH) -> Optional[pd.DataFrame]:
    """Load index from disk if it exists."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                index_df = pickle.load(f)
            # Ensure strictly a DataFrame
            if isinstance(index_df, pd.DataFrame):
                return index_df
        except Exception as e:
            print(f"Error loading index: {e}")
            return None
    return None


def extract_text_recursive(obj: Any, parent_key: str = "") -> List[str]:
    """Recursively extract text from nested dictionaries and lists."""
    texts = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Skip UI-specific keys that confuse the RAG
            if key in ['x', 'y', 'width', 'height', 'color', 'rotation', 'createdAt', 'updatedAt', 'style', 'zIndex']:
                continue
            
            full_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, (dict, list)):
                texts.extend(extract_text_recursive(value, full_key))
            elif value is not None and str(value).strip():
                texts.append(f"{full_key}: {value}")
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                texts.extend(extract_text_recursive(item, parent_key))
            elif item is not None and str(item).strip():
                texts.append(f"{parent_key}: {item}")
    
    return texts


def extract_searchable_text(item: Dict[str, Any]) -> str:
    """Extract searchable text from a board item."""
    text_parts = extract_text_recursive(item)
    return " | ".join(text_parts)


def get_embeddings(text: str, output_dim: int = EMBEDDING_DIM) -> Optional[List[float]]:
    """Generate embeddings for text using Vertex AI."""
    try:
        # Rate limit protection (simple sleep)
        time.sleep(0.05) 
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[text],
            config=EmbedContentConfig(output_dimensionality=output_dim),
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None


def build_index(board_items: List[Dict[str, Any]], existing_index: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Build searchable index from board items with strict synchronization.
    Items in 'existing_index' that are NOT in 'board_items' are discarded.
    """
    
    # 1. Create a quick lookup map from the Cache (if it exists)
    # Map ID -> {Hash, DataRow}
    cache_map = {}
    if existing_index is not None and not existing_index.empty:
        # Convert DataFrame to dictionary for O(1) access
        # Assuming 'id' is unique
        for _, row in existing_index.iterrows():
            cache_map[row["id"]] = row.to_dict()

    # 2. Identify Deletions for Stats
    # Get IDs currently on the board
    current_ids = set(item.get("id") for item in board_items if item.get("id"))
    # Get IDs currently in the cache
    cached_ids = set(cache_map.keys())
    
    # Calculate difference
    ids_to_delete = cached_ids - current_ids
    
    stats = {
        "total_source": len(board_items),
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "deleted_from_cache": len(ids_to_delete)
    }

    print(f"Syncing Index: Found {len(ids_to_delete)} items to remove from cache.")

    # 3. Build the NEW index strictly from current board_items
    new_index_data = []
    
    for item in board_items:
        item_id = item.get("id")
        
        # Skip items without ID
        if not item_id:
            continue

        item_hash = compute_item_hash(item)
        searchable_text = extract_searchable_text(item)
        
        if not searchable_text.strip():
            continue
        
        # LOGIC: Check if we can reuse the cached embedding
        if item_id in cache_map:
            cached_item = cache_map[item_id]
            
            # Use 'get' for hash in case pickle structure changed slightly
            if cached_item.get("hash") == item_hash:
                # MATCH: Reuse entire row (embedding + metadata)
                stats["unchanged"] += 1
                new_index_data.append(cached_item)
                continue
            else:
                # ID exists, but Content changed: Re-embed
                stats["updated"] += 1
                print(f"Updating content for: {item_id[:30]}...")
        else:
            # New ID: Create
            stats["new"] += 1
            print(f"Indexing new item: {item_id[:30]}...")
        
        # If we are here, we need to generate an embedding (New or Updated)
        embeddings = get_embeddings(searchable_text)
        
        if embeddings:
            new_index_data.append({
                "id": item_id,
                "text": searchable_text,
                "embeddings": embeddings,
                "item": item,
                "hash": item_hash
            })
    
    # 4. Create the strictly synced DataFrame
    # If board_items was empty, we return an empty DataFrame (cache is effectively wiped)
    if not new_index_data:
        return pd.DataFrame(columns=["id", "text", "embeddings", "item", "hash"]), stats

    return pd.DataFrame(new_index_data), stats


def search(query: str, index_df: pd.DataFrame, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search the index for relevant items."""
    if index_df is None or index_df.empty:
        return []

    # Get query embedding
    query_embedding = get_embeddings(query)
    if not query_embedding:
        return []
    
    # Calculate cosine similarity
    query_emb_array = np.array([query_embedding])
    
    # Ensure embeddings column is numpy array of lists
    try:
        index_embeddings = np.array(index_df["embeddings"].tolist())
    except Exception as e:
        print(f"Error processing embedding list: {e}")
        return []
    
    similarities = cosine_similarity(query_emb_array, index_embeddings)[0]
    
    # Get top k results
    # Ensure we don't ask for more items than exist
    actual_k = min(top_k, len(index_df))
    if actual_k == 0:
        return []

    top_indices = np.argsort(similarities)[-actual_k:][::-1]
    
    results = []
    for idx in top_indices:
        results.append({
            "id": index_df.iloc[idx]["id"],
            "text": index_df.iloc[idx]["text"],
            "similarity": float(similarities[idx]),
            "item": index_df.iloc[idx]["item"]
        })
    
    return results


def initialize_rag(data_path: str = "output/board_items.json", force_rebuild: bool = False) -> pd.DataFrame:
    """Initialize RAG system by syncing logic."""
    
    board_items = load_board_items(data_path)
    
    # Try to load existing index
    existing_index = None if force_rebuild else load_index()
    
    if existing_index is not None:
        print(f"Loaded cache with {len(existing_index)} items.")
    
    # Build/Sync Index
    index_df, stats = build_index(board_items, existing_index)
    
    print(f"\nIndex Sync Statistics:")
    print(f"  Deleted (Removed from cache): {stats['deleted_from_cache']}")
    print(f"  New (Embedded): {stats['new']}")
    print(f"  Updated (Re-embedded): {stats['updated']}")
    print(f"  Unchanged (Reused): {stats['unchanged']}")
    print(f"  Total Active Items: {len(index_df)}")
    
    # Save the strictly synced index
    save_index(index_df)
    
    return index_df


def query_rag(query: str, index_df: pd.DataFrame, top_k: int = 3, return_raw: bool = False):
    """Query the RAG system."""
    if index_df.empty:
        print("Warning: RAG Index is empty.")
        return [] if return_raw else "No data available."

    print(f"Searching for: {query}")
    results = search(query, index_df, top_k=top_k)
    
    if return_raw:
        return results
    
    return results

def run_rag(query, top_k=3):
   """Entry point helper."""
   print(f"RAG system running for query: {query}")
   # In a real app, you might want to load index once globally, 
   # but here we initialize to ensure sync
   index = initialize_rag() 
   results = query_rag(query, index, top_k=top_k, return_raw=True)
   print(f"RAG system returned {len(results)} results.")
   return results

# Example usage
if __name__ == "__main__":
    import sys
    start = time.time()
    
    force_rebuild = "--rebuild" in sys.argv
    
    # Initialize RAG
    index = initialize_rag(force_rebuild=force_rebuild)
    
    # Example queries
    test_queries = [
        "Give me summary of the patient",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        results = query_rag(query, index, top_k=2, return_raw=True)
        for i, result in enumerate(results, 1):
            print(f"\n[Result {i}] (Relevance: {result['similarity']:.3f})")
            print(f"ID: {result['id']}")
            
    end = time.time()
    print("\nExecution time:", end - start, "seconds")