# app/pipelines/webartsy/stages.py

from enum import StrEnum


class WebArtsyStage(StrEnum):
    TECHNOLOGY = "technology_detection"
    PERFORMANCE = "performance_seo"
    WEBSITE = "website_analysis"
    BUSINESS_PAGES = "business_pages"
    CONTACTS = "contacts"
    PEOPLE = "people_analysis"
    PERSON_PERSISTENCE = "person_persistence"
    PERSON_EMAIL = "person_email"