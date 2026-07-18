from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Article
from app.analysis.embeddings import generate_embedding, _get_client
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])

class ChatRequest(BaseModel):
    query: str

class SourceArticle(BaseModel):
    id: str
    headline: str
    source: str
    url: str
    published_at: Optional[str] = None
    oil_impact: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceArticle]

@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest, db: Session = Depends(get_db)):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # 1. Embed the user's question
    query_vector = generate_embedding(query)
    if not query_vector:
        raise HTTPException(status_code=500, detail="Failed to generate embedding for query.")
    
    # 2. Retrieve top 5 most relevant articles using pgvector cosine_distance
    # We only want articles that actually have an embedding
    articles = (
        db.query(Article)
        .filter(Article.embedding.isnot(None))
        .order_by(Article.embedding.cosine_distance(query_vector))
        .limit(5)
        .all()
    )
    
    if not articles:
        return ChatResponse(
            answer="I couldn't find any relevant news articles in the database to answer your question.",
            sources=[]
        )
    
    # 3. Augment: Build the prompt with retrieved context
    context_text = ""
    sources = []
    for i, a in enumerate(articles, start=1):
        pub_date = a.published_at.strftime("%Y-%m-%d") if a.published_at else "Unknown Date"
        context_text += f"[{i}] {a.headline} (Source: {a.source}, Date: {pub_date})\n"
        if a.description:
            context_text += f"    Summary: {a.description}\n\n"
            
        sources.append(
            SourceArticle(
                id=a.id,
                headline=a.headline,
                source=a.source or "Unknown",
                url=a.url,
                published_at=pub_date,
                oil_impact=a.oil_impact
            )
        )
        
    system_prompt = f"""You are an expert oil market analyst and geopolitical intelligence assistant.
Your goal is to answer the user's question based strictly on the provided Context (news articles).

RULES:
1. Base your answer ONLY on the provided articles. Do not hallucinate outside information.
2. If the context does not contain enough information to fully answer the question, state exactly what is missing or say "I don't know based on the provided news."
3. Keep the answer concise, analytical, and professional (1-3 paragraphs).
4. Use inline citations referencing the article number, e.g., "[1]" or "[2], [4]".

CONTEXT (Scraped Articles):
{context_text}
"""

    # 4. Generate the answer using OpenAI
    client = _get_client()
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured.")
        
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_CLASSIFIER_MODEL,  # usually gpt-4o-mini
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=500
        )
        answer = response.choices[0].message.content
        
        return ChatResponse(
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI generation failed: {str(e)}")
