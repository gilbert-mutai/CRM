from django.contrib.auth.tokens import PasswordResetTokenGenerator


class InvitationTokenGenerator(PasswordResetTokenGenerator):
    """
    Custom token generator for invitation links.
    Only hashes user PK and timestamp — ignores password, is_active, and other mutable fields.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Hash only immutable user data.
        Excludes password, is_active, and is_staff so they can change without invalidating the token.
        """
        return str(user.pk) + str(timestamp)


invitation_token_generator = InvitationTokenGenerator()