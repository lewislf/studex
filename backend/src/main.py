from database.database import *

def main():
    print("Fluxo de Cadastro\n")
    email = input("Email: ")
    name = input("Nome: ")
    passwd = input("Password: ")

    init_db()
    save_user_db(name, passwd, email)
    print_all_people_db()

    print("Procure por um nome!\n")
    qry_name = input("Nome para busca:")
    my_users = get_users_db(qry_name)

    print("\nImprimindo usuários correspondentes:")
    for user in my_users:
        print(user)

if __name__ == "__main__":
    main()
