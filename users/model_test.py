from users.model import User


_API_KEY = "abcd-1345-6789"

def test_user_creation_hashes_api_key():
    user = User(id=1, api_key=_API_KEY)

    assert user.api_key != _API_KEY
    assert user.is_api_user()

def test_user_creation_from_db_does_not_hash_api_key():
    user = User.model_validate({"id": 1, "api_key": _API_KEY}, context={"already_hashed": True})

    assert user.api_key == _API_KEY
    assert user.is_api_user()
