from app.models.persistence import Source, SourceRecord


def test_source_table_tracks_origin_identity() -> None:
    columns = Source.__table__.columns

    assert Source.__tablename__ == "sources"
    assert "name" in columns
    assert "source_type" in columns
    assert columns["name"].unique is True


def test_source_record_table_tracks_provider_record_and_company_link() -> None:
    columns = SourceRecord.__table__.columns
    foreign_keys = {
        foreign_key.target_fullname for column in columns for foreign_key in column.foreign_keys
    }

    assert SourceRecord.__tablename__ == "source_records"
    assert "provider_name" in columns
    assert "external_id" in columns
    assert "raw_data" in columns
    assert "collected_at" in columns
    assert "sources.id" in foreign_keys
    assert "companies.id" in foreign_keys
