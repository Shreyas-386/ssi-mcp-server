from constants import stock_list
from utils import AlertUtils


def test_source_fields_are_averaged_for_change():
    ticker = stock_list[0]
    data = [
        {"fields": "one_day_st_change_percent", ticker: 100},
        {"fields": "one_day_news_change_percent", ticker: 50},
    ]
    result = AlertUtils().get_alert_data(
        data,
        "one_day_st_change_percent",
        "one_day_news_change_percent",
        only_faang=False,
        page=1,
    )
    assert result[0] == 75


def test_raw_source_value_can_be_selected_for_suppression():
    ticker = stock_list[0]
    data = [
        {"fields": "one_day_st", ticker: 3},
        {"fields": "one_day_news", ticker: 4},
    ]
    utils = AlertUtils()
    social = utils.get_alert_data(data, "one_day_st", "one_day_news", False, 1, is_buzz=True)
    news = utils.get_alert_data(data, "one_day_st", "one_day_news", False, 1)
    assert social[0] == 7
    assert news[0] == 3.5
