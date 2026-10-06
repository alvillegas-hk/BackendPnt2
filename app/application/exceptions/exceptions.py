class ApplicationException(Exception):
    pass


class InvalidInputError(ApplicationException):
    pass


class AuthenticationError(ApplicationException):
    pass


class AuthorizationError(ApplicationException):
    pass


class RateLimitError(ApplicationException):
    pass


class UserNotFoundError(ApplicationException):
    pass


class EmailAlreadyExistsError(ApplicationException):
    pass
