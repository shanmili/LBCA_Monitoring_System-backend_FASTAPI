from database import sync_engine, Base
import models

def init_db():
    print("Creating database tables...")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    init_db()