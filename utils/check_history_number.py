from datetime import datetime
from pprint import pprint

from requests import Session

from settings import LOGIN, PASSWORD, headers_auth, headers_L2_stationar
from utils.l2_requests import authorization_L2, check_operation_protocol


def check_history_number(history_number: str) -> bool:
    session = Session()
    # authorization_L2(connect=session, login=LOGIN, password=PASSWORD, headers=headers_auth)
    return True


def check_for_protocols(history_number: str) -> bool:
    session = Session()
    authorization_L2(connect=session, login=LOGIN, password=PASSWORD, headers=headers_auth)
    result = check_operation_protocol(connect=session, history_number=int(history_number), headers=headers_L2_stationar).get('data')
    if len(result) == 0:
        return False
    else:
        for item in result:
            if item.get('researches') == ['Протокол операции (тр)'] or item.get('researches') == ['Предоперационный эпикриз']:
                if datetime.today().strftime('%d.%m.%Y') in item.get('date_create'):
                    return True
                else:
                    return False
            return False
    pprint(result)
