#
# Серверное приложение для соединений
#


import asyncio
from asyncio import transports
from pyexpat.errors import messages


class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):

        decoded = data.decode()
        if self.login is not None:
            self.send_message(decoded)
            if len(self.server.messages_history) < 10:
                self.server.messages_history.append(f'{self.login}: {decoded}')
            else:
                del self.server.messages_history[0]
                self.server.messages_history.append(f'{self.login}: {decoded}')
            print(decoded.strip('\n'))
        # переместила блок вывода данных в файл сервер ниже, в условие
        # чтобы при регистрации клиента с логином, который уже занят,
        # перед его отключением в сервере не выводилась лишняя информация
        else:
            if decoded.startswith("login:"):
                self.login = decoded.replace("login:", "").strip().replace("\r\n", "")
                if self.login not in self.server.list_of_names:
                    print(decoded.strip('\n'))
                    self.server.list_of_names.append(self.login)
                    self.transport.write(f"Привет, {self.login}!\n".encode())
                    self.transport.write(f'Сейчас в чате: {self.server.list_of_names}\n'.encode())
                    # добавила также вывод списка активных пользователей при подключении в чат
                    self.send_history()
                else:
                    self.transport.write(f"Логин {self.login} занят, попробуйте другой\n".encode())
                    self.connection_lost(exception='Login is already in use')
            else:
                self.transport.write("Неправильный логин\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")
        self.transport.write('Введите комбинацию "login:" + свой логин\n'.encode())

    # добавила в connection_made сообщение для клиента
    # иначе ему будет сложновато понять, что от него хотят после подключения

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def send_history(self):
        [self.transport.write(_.encode()) for _ in self.server.messages_history]

    def send_message(self, content: str):
        message = f"{self.login}: {content}\n"

        for user in self.server.clients:
            user.transport.write(message.encode())


class Server:
    clients: list
    list_of_names: list
    messages_history: list

    def __init__(self):
        self.clients = []
        self.list_of_names = []
        self.messages_history = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
