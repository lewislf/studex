from database.database import *

def main():
    email = input("Email: ")
    name = input("Nome: ")
    passwd = input("Password: ")

    init_db()
    save_user(name, passwd, email)
    print_all_people()

if __name__ == "__main__":
    main()
