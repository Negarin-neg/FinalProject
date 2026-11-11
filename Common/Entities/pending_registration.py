class PendingRegistration:
    """A registration that has been validated but not yet written to the
    database. It lives only in memory (see OtpService) until the one-time
    code is verified, so a half-finished sign-up never reaches the database.

    The password is kept *already hashed*, exactly like the hash the
    repository would store, so the plaintext password is never retained
    anywhere after the request that created it.
    """

    def __init__(self, first_name, last_name, mobile, username, password_hash):
        self.first_name = first_name
        self.last_name = last_name
        self.mobile = mobile
        self.username = username
        self.password_hash = password_hash
