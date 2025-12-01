import os
import boto3
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import BedrockEmbeddings

# Define the path where the vector database will be stored persistently
PERSIST_DIRECTORY = "./chroma_db"
PDF_PATH = "./kb/Aglaia_Benefit_Policy.pdf"

def create_kb_from_pdf(pdf_path: str = PDF_PATH, persist_directory: str = PERSIST_DIRECTORY) -> None:
    """
    Create a knowledge base from a PDF and store it persistently.
    
    Args:
        pdf_path: Path to the PDF file
        persist_directory: Directory to store the vector database
    """
    # Create AWS Bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )
    
    # Initialize embeddings
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1"
    )
    
    # Load and process the PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Split the documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    
    # Create and persist the vector store
    Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    print(f"Knowledge base created and stored at {persist_directory}")

def retrieve_context(query: str, persist_directory: str = PERSIST_DIRECTORY, k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant context for a query from the knowledge base.
    
    Args:
        query: The query string
        persist_directory: Directory where the vector database is stored
        k: Number of documents to retrieve
        
    Returns:
        List of dictionaries containing the retrieved documents and their metadata
    """
    # Create AWS Bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )
    
    # Initialize embeddings
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1"
    )
    
    # Load the existing vector store
    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    
    # Retrieve the most similar documents
    results = vectordb.similarity_search_with_score(query, k=k)
    
    # Format results
    retrieved_docs = []
    for doc, score in results:
        retrieved_docs.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "relevance_score": float(score) 
        })
    
    return retrieved_docs

def pdf_knowledge_retrieval(query: str) -> Dict[str, Any]:
    """
    This function retrieves information from a PDF knowledge base based on the query.
    
    Args:
        query: The question or query to search for in the knowledge base
        
    Returns:
        Dictionary with retrieved contexts and their metadata
    """
    try:
        # Check if the knowledge base exists, if not create it
        if not os.path.exists(PERSIST_DIRECTORY):
            print("Knowledge base not found. Creating new knowledge base...")
            create_kb_from_pdf()
        
        contexts = retrieve_context(query)
        return {
            "status": "success",
            "query": query,
            "contexts": contexts
        }
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e)
        }

# If this script is run directly, set up the knowledge base
if __name__ == "__main__":
    # Check if the knowledge base already exists
    if not os.path.exists(PERSIST_DIRECTORY):
        print("Setting up knowledge base...")
        create_kb_from_pdf()
    else:
        print(f"Knowledge base already exists at {PERSIST_DIRECTORY}")
        
    # Example query to test the knowledge base
    test_query = "What are the medical benefits offered?"
    result = pdf_knowledge_retrieval(test_query)
    print("\nTest Query:", test_query)
    print("Result:", result)