from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    narrative_text = Column(Text)

    subcategories = relationship("Subcategory", back_populates="category")


class Subcategory(Base):
    __tablename__ = "subcategories"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category_id = Column(String, ForeignKey("categories.id"))
    narrative_text = Column(Text)

    category = relationship("Category", back_populates="subcategories")
    theses = relationship("Thesis", back_populates="subcategory")


class Thesis(Base):
    __tablename__ = "theses"

    id = Column(Integer, primary_key=True)
    running_number = Column(Integer, unique=True, nullable=False)

    author = Column(String, nullable=False)
    profession = Column(String)
    university = Column(String)
    year = Column(Integer)
    title = Column(Text, nullable=False)
    degree_type = Column(String, default="Doktorsavhandling")

    category_id = Column(String)
    subcategory_id = Column(String, ForeignKey("subcategories.id"))

    source = Column(String)
    abstract = Column(Text)
    dissertation_url = Column(String)
    pdf_url = Column(String)
    doi = Column(String)
    urn = Column(String)
    metadata_status = Column(String, default="not_started", nullable=False)
    metadata_last_checked_at = Column(DateTime)

    subcategory = relationship("Subcategory", back_populates="theses")
    included_papers = relationship("IncludedPaper", back_populates="thesis")


class IncludedPaper(Base):
    __tablename__ = "included_papers"

    id = Column(Integer, primary_key=True)
    thesis_id = Column(Integer, ForeignKey("theses.id"), nullable=False)
    title = Column(Text, nullable=False)
    journal = Column(String)
    year = Column(Integer)
    doi = Column(String)
    pubmed_id = Column(String)
    url = Column(String)
    abstract = Column(Text)

    thesis = relationship("Thesis", back_populates="included_papers")


class DiscoveryCandidate(Base):
    __tablename__ = "discovery_candidates"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    author = Column(String)
    university = Column(String)
    year = Column(Integer)
    abstract = Column(Text)
    source = Column(String, nullable=False)
    source_host = Column(String)
    source_url = Column(String)
    pdf_url = Column(String)
    publication_type = Column(String)
    doi = Column(String)
    urn = Column(String)
    matched_keywords = Column(Text)
    keyword_group = Column(String)
    match_status = Column(String, default="new_candidate", nullable=False)
    similarity_to_existing = Column(Float)
    matched_existing_thesis_id = Column(Integer)
    matched_existing_running_number = Column(Integer)
    review_status = Column(String, default="needs_review", nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Reference(Base):
    __tablename__ = "references"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True, nullable=False)
    text = Column(Text, nullable=False)
