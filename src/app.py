import json
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import csv
import concurrent.futures
import random
from kafka import KafkaConsumer, KafkaProducer
import uvicorn

# Load environment variables
load_dotenv()

# Create SQLAlchemy engine for PostgreSQL
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_db = os.getenv("POSTGRES_DB")

# Sử dụng các biến môi trường trong kết nối đến cơ sở dữ liệu PostgreSQL, ví dụ:
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@localhost:5432/mydb"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create SQLAlchemy session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define SQLAlchemy model
class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    rating = Column(Integer)

# Create table in PostgreSQL database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Function to process CSV data and save to PostgreSQL
def process_csv_data_postgres(row):
    db = SessionLocal()
    hotel = Hotel(name=row['name'], address=row['address'], rating=int(row['rating']))
    db.add(hotel)
    db.commit()
    db.close()

# Function to generate data and write to data.csv file
def generate_data_to_csv(file_path, num_records=10):
    hotel_names = ["Grand Hotel", "Luxury Resort", "Seaside Inn", "Mountain Lodge", "City Center Hotel"]
    addresses = ["123 Main Street", "456 Elm Avenue", "789 Oak Boulevard", "101 Pine Road", "202 Maple Lane"]
    ratings = [4, 4.5, 5]

    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ['name', 'address', 'rating']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for _ in range(num_records):
            hotel_name = random.choice(hotel_names)
            address = random.choice(addresses)
            rating = random.choice(ratings)
            writer.writerow({'name': hotel_name, 'address': address, 'rating': rating})

# Endpoint to upload CSV file and save data to PostgreSQL
@app.post("/upload-file/")
async def upload_csv_file(file: UploadFile = File(...)):
    with open(file.filename, "wb") as buffer:
        buffer.write(await file.read())
    
    with open(file.filename, 'r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]

    # Use ThreadPoolExecutor to process data concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Process data and save to PostgreSQL
        postgres_futures = [executor.submit(process_csv_data_postgres, row) for row in data]

        # Wait for all tasks to complete
        concurrent.futures.wait(postgres_futures)

    return {"message": "Data saved successfully"}

# Endpoint to generate data and write to data.csv file
@app.post("/generate-data/")
async def generate_data(num_records: int = Form(...)):
    generate_data_to_csv('data.csv', num_records=num_records)
    return {"message": f"{num_records} records generated and written to data.csv successfully"}

# Endpoint to get top N hotels from PostgreSQL
@app.get("/top-hotels/")
async def get_top_hotels(N: int):
    db = SessionLocal()
    hotels = db.query(Hotel).order_by(Hotel.rating.desc()).limit(N).all()
    db.close()
    return hotels

import boto3
from pydantic import BaseModel
# Initialize Kinesis client
kinesis_client = boto3.client(
    'kinesis',
    aws_access_key_id="AKIAQE2DNCJWXYQVJUFJ",
    aws_secret_access_key="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",
    region_name="ap-southeast-1"
)
dynamodb = boto3.client(
    'dynamodb',
    aws_access_key_id="AKIAQE2DNCJWXYQVJUFJ",
    aws_secret_access_key="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",
    region_name="ap-southeast-1"
)
class WeatherData(BaseModel):
    city: str
    temperature: float
    humidity: float
    timestamp: int

@app.post("/weather")
async def receive_weather_data(weather_data: WeatherData):
    try:
        # Send weather data to Amazon Kinesis
        data = {
            "city": weather_data.city,
            "temperature": weather_data.temperature,
            "humidity": weather_data.humidity,
            "timestamp": weather_data.timestamp
        }
        response = kinesis_client.put_record(
            StreamName="test",
            Data=json.dumps(data),
            PartitionKey=weather_data.city
        )
        print(f"Weather data sent to Kinesis. SequenceNumber: {response['SequenceNumber']}, ShardId: {response['ShardId']}, Data: {data}")
        return {"message": "Weather data received successfully"}
    except Exception as e:
        print(f"Error: {e}")

@app.get("/weather/{city}")
async def get_weather_data(city: str, sequence_number: int):
    try:
        response = kinesis_client.get_shard_iterator(
            StreamName="test",
            ShardId="shardId-000000000002",
            ShardIteratorType="AT_SEQUENCE_NUMBER",
            StartingSequenceNumber=str(sequence_number)
        )
        shard_iterator = response["ShardIterator"]

        records_response = kinesis_client.get_records(
            ShardIterator=shard_iterator,
            Limit=10  # Adjust the number of records to fetch as needed
        )
        
        records = []
        for record in records_response["Records"]:
            data = record["Data"].decode("utf-8")
            weather_data = json.loads(data)
            if weather_data["city"] == city:
                records.append(weather_data)
        
        return {
            "message": "Weather data retrieved successfully",
            "city": city,
            "weather_data": records
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
class Item(BaseModel):
    id: str
    name: str

@app.post("/items/")
async def create_item(item: Item):
    try:
        response = dynamodb.put_item(
            TableName='test',
            Item={
                'id': {'S': item.id},
                'name': {'S': item.name}
            }
        )
        return {"message": "Item created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    try:
        response = dynamodb.get_item(
            TableName='test',
            Key={
                'id': {'S': item_id}
            }
        )
        item = response.get('Item')
        if item:
            return {"id": item['id']['S'], "name": item['name']['S']}
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
