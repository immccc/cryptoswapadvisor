from users.db.sql.model import User as UserSQLModel
from users.model import User


def map_user(user: UserSQLModel) -> User:
    return User.model_validate(
        {
            "id": user.id,
            "api_key": user.api_key,
        },
        context={"already_hashed": True},
    )
