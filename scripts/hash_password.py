from getpass import getpass

from security import hash_password


def main():
    password = getpass("New admin password: ")
    confirmation = getpass("Confirm admin password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    print(hash_password(password))


if __name__ == "__main__":
    main()
