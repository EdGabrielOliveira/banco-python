import textwrap
import json
import os

# Constantes
LIMITE_SAQUES = 3
AGENCIA = "0001"
USUARIOS_FILE = "usuarios.json"
CONTAS_FILE = "contas.json"


def carregar_dados(arquivo):
    """Carrega dados de um arquivo JSON."""
    if os.path.exists(arquivo):
        with open(arquivo, "r") as f:
            return json.load(f)
    return []


def salvar_dados(arquivo, dados):
    """Salva dados em um arquivo JSON."""
    with open(arquivo, "w") as f:
        json.dump(dados, f, indent=4)


def menu():
    """Exibe o menu e retorna a opção escolhida."""
    menu_text = """\n
    ================ MENU ================
    [d]\tDepositar
    [s]\tSacar
    [e]\tExtrato
    [nc]\tNova conta
    [lc]\tListar contas
    [nu]\tNovo usuário
    [q]\tSair
    => """
    return input(textwrap.dedent(menu_text))


def validar_valor(valor):
    """Valida se o valor é um número positivo."""
    try:
        valor = float(valor)
        if valor > 0:
            return valor
        else:
            print("\n@@@ Operação falhou! O valor informado é inválido. @@@")
            return None
    except ValueError:
        print("\n@@@ Operação falhou! O valor informado é inválido. @@@")
        return None


def depositar(saldo, valor, extrato):
    """Realiza um depósito."""
    saldo += valor
    extrato += f"Depósito:\tR$ {valor:.2f}\n"
    print("\n=== Depósito realizado com sucesso! ===")
    return saldo, extrato


def sacar(saldo, valor, extrato, limite, numero_saques, limite_saques):
    """Realiza um saque, se possível."""
    excedeu_saldo = valor > saldo
    excedeu_limite = valor > limite
    excedeu_saques = numero_saques >= limite_saques

    if excedeu_saldo:
        print("\n@@@ Operação falhou! Você não tem saldo suficiente. @@@")
    elif excedeu_limite:
        print("\n@@@ Operação falhou! O valor do saque excede o limite. @@@")
    elif excedeu_saques:
        print("\n@@@ Operação falhou! Número máximo de saques excedido. @@@")
    else:
        saldo -= valor
        extrato += f"Saque:\t\tR$ {valor:.2f}\n"
        numero_saques += 1
        print("\n=== Saque realizado com sucesso! ===")

    return saldo, extrato, numero_saques


def exibir_extrato(saldo, extrato):
    """Exibe o extrato da conta."""
    print("\n================ EXTRATO ================")
    print("Não foram realizadas movimentações." if not extrato else extrato)
    print(f"\nSaldo:\t\tR$ {saldo:.2f}")
    print("==========================================")


def criar_usuario(usuarios):
    """Cria um novo usuário."""
    cpf = input("Informe o CPF (somente número): ")
    usuario = filtrar_usuario(cpf, usuarios)

    if usuario:
        print("\n@@@ Já existe usuário com esse CPF! @@@")
        return

    nome = input("Informe o nome completo: ")
    data_nascimento = input("Informe a data de nascimento (dd-mm-aaaa): ")
    endereco = input("Informe o endereço (logradouro, nro - bairro - cidade/sigla estado): ")

    usuarios.append({"nome": nome, "data_nascimento": data_nascimento, "cpf": cpf, "endereco": endereco})
    salvar_dados(USUARIOS_FILE, usuarios)
    print("=== Usuário criado com sucesso! ===")


def filtrar_usuario(cpf, usuarios):
    """Filtra e retorna um usuário pelo CPF."""
    return next((usuario for usuario in usuarios if usuario["cpf"] == cpf), None)


def criar_conta(agencia, numero_conta, usuarios, contas):
    """Cria uma nova conta bancária."""
    cpf = input("Informe o CPF do usuário: ")
    usuario = filtrar_usuario(cpf, usuarios)

    if usuario:
        conta = {"agencia": agencia, "numero_conta": numero_conta, "usuario": usuario}
        contas.append(conta)
        salvar_dados(CONTAS_FILE, contas)
        print("\n=== Conta criada com sucesso! ===")
    else:
        print("\n@@@ Usuário não encontrado, fluxo de criação de conta encerrado! @@@")


def listar_contas(contas):
    """Lista todas as contas cadastradas."""
    for conta in contas:
        linha = f"""\
            Agência:\t{conta['agencia']}
            C/C:\t\t{conta['numero_conta']}
            Titular:\t{conta['usuario']['nome']}
        """
        print("=" * 50)
        print(textwrap.dedent(linha))
    print("=" * 50)


def main():
    saldo = 0
    limite = 500
    extrato = ""
    numero_saques = 0

    # Carregar dados persistidos
    usuarios = carregar_dados(USUARIOS_FILE)
    contas = carregar_dados(CONTAS_FILE)

    while True:
        opcao = menu()

        if opcao == "d":
            valor = validar_valor(input("Informe o valor do depósito: "))
            if valor:
                saldo, extrato = depositar(saldo, valor, extrato)

        elif opcao == "s":
            valor = validar_valor(input("Informe o valor do saque: "))
            if valor:
                saldo, extrato, numero_saques = sacar(
                    saldo=saldo,
                    valor=valor,
                    extrato=extrato,
                    limite=limite,
                    numero_saques=numero_saques,
                    limite_saques=LIMITE_SAQUES,
                )

        elif opcao == "e":
            exibir_extrato(saldo, extrato)

        elif opcao == "nu":
            criar_usuario(usuarios)

        elif opcao == "nc":
            numero_conta = len(contas) + 1
            criar_conta(AGENCIA, numero_conta, usuarios, contas)

        elif opcao == "lc":
            listar_contas(contas)

        elif opcao == "q":
            print("Saindo do sistema. Até mais!")
            break

        else:
            print("Operação inválida, por favor selecione novamente a operação desejada.")


if __name__ == "__main__":
    main()
