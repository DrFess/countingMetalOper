from pprint import pprint

from requests import Session

from settings import LOGIN, PASSWORD, headers_auth, headers_L2_stationar
from utils.l2_requests import authorization_L2, create_protocol, get_protocol_info, save_protocol_data


def create_protocols_func(history_number: str):
    """Создаёт протоколы предоперационный и операции"""
    session = Session()
    authorization_L2(connect=session, login=LOGIN, password=PASSWORD, headers=headers_auth)

    create_protocol(connect=session, history_number=int(history_number), service_id=479, headers=headers_L2_stationar)  # предоперационный

    operative = create_protocol(connect=session, history_number=int(history_number), service_id=5, headers=headers_L2_stationar)  # операция
    direction_pk = operative.get('pk')
    protocol_info = get_protocol_info(connect=session, pk=direction_pk, headers=headers_L2_stationar)
    save_protocol_data(
        connect=session,
        pk=protocol_info.get('pk'),
        direction_pk=direction_pk,
        history_number=int(history_number),
        implant='спица тестово',
        count_implant='1',
        examination_date=protocol_info.get('examination_date'),
        headers=headers_L2_stationar
    )

