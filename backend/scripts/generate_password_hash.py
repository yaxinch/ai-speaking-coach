"""Interactively generate a bcrypt hash for ADMIN_PASSWORD_HASH."""

from getpass import getpass

import bcrypt


def main() -> None:
    password = getpass("Admin password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    print(bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"))


if __name__ == "__main__":
    main()
