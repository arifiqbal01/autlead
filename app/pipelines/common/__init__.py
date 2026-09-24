# app/pipelines/common/__init__.py

from app.pipelines.common.contacts import (
    ContactAnalysisResult,
    analyze_contacts,
)
from app.pipelines.common.people import (
    AnalyzedPerson,
    ClassifiedPerson,
    PeopleAnalysisResult,
    analyze_people,
    select_best_decision_maker,
    select_decision_makers,
)
from app.pipelines.common.website_crawl import (
    WebsiteAnalysisResult,
    analyze_website,
)
from app.pipelines.common.person_email import (
    PersonEmailAnalysisResult,
    PersonEmailResult,
    PersonEmailTarget,
    analyze_person_emails,
)
from .website_pages import WebsitePageCollectionResult, collect_business_pages


__all__ = [

    # Website crawling
    "WebsiteAnalysisResult",
    "analyze_website",

    # Contacts
    "ContactAnalysisResult",
    "analyze_contacts",

    # People
    "AnalyzedPerson",
    "ClassifiedPerson",
    "PeopleAnalysisResult",
    "analyze_people",
    "select_best_decision_maker",
    "select_decision_makers",

    # person email
    "PersonEmailAnalysisResult",
    "PersonEmailResult",
    "PersonEmailTarget",
    "analyze_person_emails",

    # business pages
    "WebsitePageCollectionResult",
    "collect_business_pages"
]