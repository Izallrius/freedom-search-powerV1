from database.models import Base, crawler_engine, indexer_engine

def init_databases():
    print("Creating database tables...")
    Base.metadata.create_all(crawler_engine)
    Base.metadata.create_all(indexer_engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_databases() 