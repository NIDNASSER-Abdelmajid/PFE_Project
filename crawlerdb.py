import logging
import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (create_engine, Column, Integer, String,
                        DateTime, Enum, Boolean, JSON, ForeignKey,
                        SmallInteger, Text, exc)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone


Base = declarative_base()

class Website(Base):
    __tablename__ = 'websites'
    website_id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, unique=True)
    visited_status = Column(Enum('pending', 'completed', 'failed', name='visit_status_enum'), nullable=False)
    visit_timestamp = Column(DateTime)
    category = Column(String(50))

    requests = relationship("NetworkRequest", back_populates="website")
    cookies = relationship("Cookie", back_populates="website")
    files = relationship("DownloadedFile", back_populates="website")


class NetworkRequest(Base):
    __tablename__ = 'network_requests'
    request_id = Column(String(64), primary_key=True)
    website_id = Column(Integer, ForeignKey('websites.website_id'), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10), nullable=False)
    resource_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    website = relationship("Website", back_populates="requests")
    response = relationship("NetworkResponse", uselist=False, back_populates="request")
    cookies = relationship("Cookie", back_populates="request")
    files = relationship("DownloadedFile", back_populates="request")


class NetworkResponse(Base):
    __tablename__ = 'network_responses'
    response_id = Column(String(64), ForeignKey('network_requests.request_id'), primary_key=True)
    status_code = Column(SmallInteger, nullable=False)
    headers = Column(JSON, nullable=False)
    security_state = Column(Enum('secure', 'insecure', 'unknown', name='security_state_enum'), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    request = relationship("NetworkRequest", back_populates="response")
    cookies = relationship("Cookie", back_populates="response")
    files = relationship("DownloadedFile", back_populates="response")


class Cookie(Base):
    __tablename__ = 'cookies'
    cookie_id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey('websites.website_id'), nullable=False)
    request_id = Column(String(64), ForeignKey('network_requests.request_id'))
    response_id = Column(String(64), ForeignKey('network_responses.response_id'))
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    expires = Column(DateTime)
    secure = Column(Boolean, nullable=False)
    http_only = Column(Boolean, nullable=False)
    value = Column(Text)
    party = Column(Enum('first', 'third', name='party_enum'), nullable=False)

    website = relationship("Website", back_populates="cookies")
    request = relationship("NetworkRequest", back_populates="cookies")
    response = relationship("NetworkResponse", back_populates="cookies")


class DownloadedFile(Base):
    __tablename__ = 'downloaded_files'
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey('websites.website_id'), nullable=False)
    request_id = Column(String(64), ForeignKey('network_requests.request_id'), nullable=False)
    response_id = Column(String(64), ForeignKey('network_responses.response_id'), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(255), nullable=False)

    website = relationship("Website", back_populates="files")
    request = relationship("NetworkRequest", back_populates="files")
    response = relationship("NetworkResponse", back_populates="files")

    @classmethod
    def safe_create(cls, session, website_id, request_id, response_id, file_type, file_path):
        """Only create if response exists"""
        if session.get(NetworkResponse, response_id):
            return cls(
                website_id=website_id,
                request_id=request_id,
                response_id=response_id,
                file_type=file_type,
                file_path=file_path
            )
        return None


class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    request_id = Column(String(64), ForeignKey('network_requests.request_id'), primary_key=True)
    rule_id = Column(Integer)
    decision = Column(Enum('AD', 'TRACKER', 'SAFE', name='decision_enum'), nullable=False)

    request = relationship("NetworkRequest")


def init_db(connection_string):
    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)
    return engine


class crawler2db:
    def __init__(self):
        load_dotenv("secure_data.env")
        connection_string = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@localhost/crawlerdb"
        self.engine = init_db(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def add_website(self, domain: str, category: str = 'Uncategorized') -> int:
        """Add website or return existing ID if already present"""
        try:
            existing = self.session.query(Website).filter_by(domain=domain).first()
            if existing:
                return existing.website_id

            website = Website(
                domain=domain,
                visited_status="pending",
                visit_timestamp=datetime.now(timezone.utc),
                category=category
            )
            self.session.add(website)
            self.session.commit()
            return website.website_id

        except Exception as e:
            self.session.rollback()
            logging.error(f"Database error adding website {domain}: {e}")
            raise

    def add_request(self, request_id, website_id, url, method, resource_type, timestamp):
        stmt = insert(NetworkRequest).values(
            request_id=request_id,
            website_id=website_id,
            url=url,
            method=method,
            resource_type=resource_type,
            timestamp=timestamp
        ).on_conflict_do_nothing(index_elements=['request_id'])

        self.session.execute(stmt)
        self.session.commit()
        return request_id

    def add_response(self, request_id: str, status_code: int, headers: dict,
                     security_state: str, timestamp: datetime) -> Optional[str]:
        """Add response with proper security state handling"""
        try:
            security_state = security_state.lower() if security_state else 'insecure'
            if security_state not in ['secure', 'insecure']:
                security_state = 'insecure'

            if not self.session.get(NetworkRequest, request_id):
                raise ValueError(f"Request {request_id} not found")

            stmt = insert(NetworkResponse).values(
                response_id=request_id,
                status_code=status_code,
                headers=headers,
                security_state=security_state,
                timestamp=timestamp
            ).on_conflict_do_update(
                index_elements=['response_id'],
                set_={
                    'status_code': status_code,
                    'headers': headers,
                    'security_state': security_state,
                    'timestamp': timestamp
                }
            )

            self.session.execute(stmt)
            self.session.commit()
            return request_id
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            logging.error(f"Error adding response for request {request_id}: {e}")
            return None

    def store_cookies(self, website_id, cookies, party, request_id=None, response_id=None):
        for cookie in cookies:
            new_cookie = Cookie(
                website_id=website_id,
                request_id=request_id,
                response_id=response_id,
                name=cookie.get('name'),
                domain=cookie.get('domain'),
                expires=datetime.fromtimestamp(cookie.get('expires'), timezone.utc) if cookie.get('expires') else None,
                secure=cookie.get('secure', False),
                http_only=cookie.get('http_only', False),
                value=cookie.get('value', ''),
                party=party
            )
            self.session.add(new_cookie)
        self.session.commit()
        return True

    def add_downloaded_file(self, website_id: int, request_id: str, file_type: str, file_path: str,
                            response_id: Optional[str] = None) -> Optional[int]:
        """Add downloaded file with optional response_id"""
        try:
            file = DownloadedFile(
                website_id=website_id,
                request_id=request_id,
                response_id=response_id,
                file_type=file_type,
                file_path=file_path
            )
            self.session.add(file)
            self.session.commit()
            return file.file_id
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            logging.error(f"Error adding downloaded file: {e}")
            return None

    def add_analysis_result(self, request_id, rule_id, decision):
        result = AnalysisResult(
            request_id=request_id,
            rule_id=rule_id,
            decision=decision
        )
        self.session.add(result)
        self.session.commit()
        return True

    def close(self):
        self.session.close()
        self.engine.dispose()
