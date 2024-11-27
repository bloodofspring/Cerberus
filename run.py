"""Run this file to start instances"""
from datetime import datetime

import pyrostep
from colorama import Fore, init

from client_handlers.activate import add_handlers
from database.create import create_tables
from instances import client


def by_alien() -> None:
    print(end="\n\n")
    print(Fore.LIGHTMAGENTA_EX + r"@@@@@@@  @@@ @@@     @@@@@@  @@@      @@@ @@@@@@@@ @@@  @@@   @@@@@             @@@@@ ")
    print(Fore.LIGHTMAGENTA_EX + r"@@!  @@@ @@! !@@    @@!  @@@ @@!      @@! @@!      @@!@!@@@ @@!@              @@!@    ")
    print(Fore.LIGHTMAGENTA_EX + r"@!@!@!@   !@!@!     @!@!@!@! @!!      !!@ @!!!:!   @!@@!!@! @!@!@!@           @!@!@!@ ")
    print(Fore.LIGHTMAGENTA_EX + r"!!:  !!!   !!:      !!:  !!! !!:      !!: !!:      !!:  !!! !!:  !!!          !!:  !!!")
    print(Fore.LIGHTMAGENTA_EX + r":: : ::    .:        :   : : : ::.: : :   : :: ::  ::    :   : : ::  .......   : : :: ")
    print(Fore.LIGHTMAGENTA_EX + r"                                                                     : :: : :         ")
    print(Fore.LIGHTMAGENTA_EX + r"                                                                                      ")
    print((
            Fore.LIGHTYELLOW_EX + f"[{datetime.now()}][!]>>-||--> " +
            Fore.LIGHTGREEN_EX + f"Клиент запущен!"
    ))


def run_bot() -> None:
    init(autoreset=True)
    add_handlers()
    create_tables()
    by_alien()
    pyrostep.listen(app=client)
    client.run()


if __name__ == "__main__":
    run_bot()
