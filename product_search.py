from sentence_transformers import SentenceTransformer
import pickle
import faiss
from pathlib import Path

def initialize_encoder():
    """Initialize or download the sentence transformer model."""
    model_path = Path("encoder_model")
    
    if not model_path.exists():
        print("Downloading encoder model (all-MiniLM-L6-v2)...")
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        encoder.save(str(model_path))
        print("Encoder model downloaded and saved successfully")
    else:
        print("Loading existing encoder model...")
        encoder = SentenceTransformer(str(model_path))
    
    return encoder

def create_vector_database(activities, agribalyse, bigclimatedata, update=False):
    """Create or load vector database for product searching."""
    vector_db_path = Path("vector_database.pkl")
    
    if update or not vector_db_path.exists():
        print("Creating new vector database...")
        bonsai_names = activities['description'].dropna().unique()
        agribalyse_names = agribalyse['product_name'].dropna().unique()
        bigclimatedata_names = bigclimatedata['Name'].dropna().unique()

        encoder = initialize_encoder()

        vector_database = {
            'BONSAI': {'index': None, 'products': bonsai_names},
            'Agribalyse': {'index': None, 'products': agribalyse_names},
            'Big Climate Database': {'index': None, 'products': bigclimatedata_names}
        }

        for name, data in vector_database.items():
            print(f"Processing {name} products...")
            products = data['products']
            product_embeddings = encoder.encode(products)
            faiss.normalize_L2(product_embeddings)
            dimension = product_embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)
            index.add(product_embeddings)
            vector_database[name]['index'] = index

        with open(vector_db_path, 'wb') as file:
            pickle.dump(vector_database, file)
        print("Vector database created and saved successfully")
    else:
        print("Loading existing vector database...")
        encoder = initialize_encoder()
        with open(vector_db_path, 'rb') as file:
            vector_database = pickle.load(file)

    return encoder, vector_database

def search_top_k(encoder, vector_database, query, k=5, similarity=False, verbose=False):
    """Search for similar products in the vector database."""
    query_embedding = encoder.encode([query])
    faiss.normalize_L2(query_embedding)
    
    results = {}
    
    for name, data in vector_database.items():
        distances, idx = data['index'].search(query_embedding, k)
        if similarity:
            results[name] = [(data['products'][j], distances[0][n]) for n, j in enumerate(idx[0])]
        else:
            results[name] = [data['products'][j] for _, j in enumerate(idx[0])]

    if verbose:
        print(f"\nProduct: '{query}'")
        for source, matches in results.items():
            print(f"\nTop {k} results from {source}:")
            for product, similarity in matches:
                print(f"- {product} (Similarity: {similarity:.4f})")
        
    return results