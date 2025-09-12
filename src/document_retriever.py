import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    WebBaseLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentRetriever:
    """
    A class to handle document loading, processing, and retrieval for the wine knowledge base.
    """
    
    def __init__(self, data_dir: str = "../data"):
        """
        Initialize the DocumentRetriever.
        
        Args:
            data_dir: Directory containing documents to be loaded
        """
        self.data_dir = Path(data_dir)
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self.documents = []
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_documents(self) -> List[Document]:
        """
        Load documents from the data directory.
        
        Returns:
            List of loaded documents
        """
        # Define loaders for different file types
        loaders = {
            ".txt": TextLoader,
            ".md": UnstructuredMarkdownLoader,
            ".pdf": PyPDFLoader,
            ".docx": UnstructuredWordDocumentLoader,
            ".pptx": UnstructuredPowerPointLoader,
            ".xlsx": UnstructuredExcelLoader,
            ".csv": CSVLoader,
        }
        
        # Load documents from the data directory
        loaded_docs = []
        
        # Get all files in the data directory and subdirectories
        for ext in loaders.keys():
            try:
                loader = DirectoryLoader(
                    str(self.data_dir),
                    glob=f"**/*{ext}",
                    loader_cls=loaders[ext],
                    show_progress=True,
                    use_multithreading=True,
                )
                docs = loader.load()
                if docs:
                    logger.info(f"Loaded {len(docs)} documents with extension {ext}")
                    loaded_docs.extend(docs)
            except Exception as e:
                logger.warning(f"Error loading documents with extension {ext}: {str(e)}")
        
        self.documents = loaded_docs
        return loaded_docs
    
    def split_documents(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
        """
        Split documents into chunks for processing.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            
        Returns:
            List of split documents
        """
        if not self.documents:
            self.load_documents()
        
        # Create a text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,
        )
        
        # Split documents
        split_docs = text_splitter.split_documents(self.documents)
        logger.info(f"Split {len(self.documents)} documents into {len(split_docs)} chunks")
        
        return split_docs
    
    def create_vector_store(self, documents: Optional[List[Document]] = None) -> None:
        """
        Create a vector store from documents.
        
        Args:
            documents: List of documents to create vector store from. If None, uses loaded documents.
        """
        if documents is None:
            if not self.documents:
                self.load_documents()
            documents = self.split_documents()
        
        logger.info("Creating vector store...")
        self.vector_store = FAISS.from_documents(documents, self.embeddings)
        logger.info(f"Created vector store with {len(documents)} documents")
    
    def save_vector_store(self, path: str = "../data/vector_store") -> None:
        """
        Save the vector store to disk.
        
        Args:
            path: Path to save the vector store
        """
        if self.vector_store is None:
            logger.warning("No vector store to save. Call create_vector_store() first.")
            return
        
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.vector_store.save_local(str(save_path))
        logger.info(f"Saved vector store to {save_path}")
    
    def load_vector_store(self, path: str = "../data/vector_store") -> bool:
        """
        Load a vector store from disk.
        
        Args:
            path: Path to the vector store
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            self.vector_store = FAISS.load_local(str(path), self.embeddings, allow_dangerous_deserialization=True)
            logger.info(f"Loaded vector store from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False
    
    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Document]:
        """
        Perform a similarity search on the vector store.
        
        Args:
            query: The query string
            k: Number of results to return
            
        Returns:
            List of documents most similar to the query
        """
        if self.vector_store is None:
            logger.warning("No vector store available. Loading or creating one...")
            if not self.load_vector_store():
                self.create_vector_store()
        
        try:
            return self.vector_store.similarity_search(query, k=k, **kwargs)
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            return []
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add new documents to the vector store.
        
        Args:
            documents: List of documents to add
        """
        if self.vector_store is None:
            logger.warning("No vector store available. Creating a new one...")
            self.create_vector_store(documents)
            return
        
        try:
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to the vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Initialize the retriever
    retriever = DocumentRetriever()
    
    # Load and process documents
    documents = retriever.load_documents()
    
    if documents:
        # Create and save vector store
        retriever.create_vector_store()
        retriever.save_vector_store()
        
        # Example search
        query = "What are the best wine and food pairings?"
        results = retriever.similarity_search(query)
        
        print(f"\nResults for query: '{query}'")
        for i, doc in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Content: {doc.page_content[:300]}...")  # Show first 300 chars
    else:
        print("No documents found in the data directory. Please add some documents to the data folder.")
        print("Supported formats: .txt, .md, .pdf, .docx, .pptx, .xlsx, .csv")
