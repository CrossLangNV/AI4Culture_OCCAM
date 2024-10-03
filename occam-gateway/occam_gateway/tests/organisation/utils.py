from datetime import datetime, timedelta, timezone

from organisation.models import Organisation, OrganisationAPIKey


def create_test_api_key():
    organisation = Organisation.objects.create(name="test-organisation")
    _, key = OrganisationAPIKey.objects.create_key(
        name="test-service",
        organisation=organisation,
        expiry_date=datetime.now(tz=timezone.utc)
        + timedelta(hours=1),  # Expire in 1 hour
    )
    return key


def create_test_api_headers():
    key = create_test_api_key()
    return {"Api-Key": key}
