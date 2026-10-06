class DomainException(Exception):
    pass


class UserNotFoundError(DomainException):
    pass


class EmailAlreadyExistsError(DomainException):
    pass


class InvalidCredentialsError(DomainException):
    pass


class InvalidPasswordError(DomainException):
    pass


class UserInactiveError(DomainException):
    pass
