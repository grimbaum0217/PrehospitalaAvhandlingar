from sqlalchemy import Column, Integer, String, Text, ForeignKey
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

    category_id = Column(String)
    subcategory_id = Column(String, ForeignKey("subcategories.id"))

    source = Column(String)

    subcategory = relationship("Subcategory", back_populates="theses")
