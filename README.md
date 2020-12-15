# gui_chat

Графический интерфейс для общения в чате.


### Окружение
Для работы необходимо создать виртуальное окружение и установить туда все зависимости:

```
virtualenv venv --python=python3
source venv/bin/activate
pip install -r requirements.txt  
```


### Конфигурация
Для работы необходимы следующие параметры, которые могут быть заданы как переменные окружения или через файл `config.conf`:

- host, env HOST - хостнейм чат сервера.
- read-port, env READ_PORT - порт для чтения из чата.
- write-port, env WRITE_PORT - порт для записи в чат.
- history, env HISTORY_FILENAME - имя файла, куда будет сохраняться переписка в чате.
- token, env TOKEN - токен для авторизации.
- username, env USERNAME - username в чате, будет зарегистрирован в .


### Регистрация
Если вы не зарегистрированы в чате, можно это сделать с помощью скрипта:

```
python register.py
```

### Чат клиент
Запуск чат клиента:
```
python client.py
```