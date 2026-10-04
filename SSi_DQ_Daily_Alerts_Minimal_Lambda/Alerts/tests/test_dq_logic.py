import pytest
from dq import (
    news_multiplier,
    news_effective_weight,
    apply_news_dq,
    reddit_dq_weight,
    apply_reddit_dq,
    effective_buzz,
    percentage_change,
    DEFAULT_NEWS_DQ_SCORES,
)
from index import SentimentAlerts, SentimentPriceAlerts
from constants import graph_types, stock_list


# ============================================================================
# 1. Multiplier & Weight Unit Tests (dq.py)
# ============================================================================

class TestNewsDQ:
    def test_news_multiplier_bands(self):
        """Test news multiplier band boundaries."""
        assert news_multiplier(None) == 1.0
        assert news_multiplier(0.80) == 1.0
        assert news_multiplier(0.85) == 1.8
        assert news_multiplier(0.90) == 1.8
        assert news_multiplier(0.95) == 3.0
        assert news_multiplier(1.00) == 3.0

    def test_news_effective_weight_known_host(self):
        """Test known host weight calculation."""
        # Bloomberg score is 1.0 -> multiplier is 3.0 -> weight = 3.0
        weight, meta = news_effective_weight("Bloomberg")
        assert weight == 3.0
        assert meta["dq_score"] == 1.0
        assert meta["dq_multiplier"] == 3.0
        assert meta["dq_status"] == "weighted"

    def test_news_effective_weight_unmapped_host(self):
        """Test eligible unmapped host weight."""
        weight, meta = news_effective_weight("Unknown Host")
        assert weight == 1.0
        assert meta["dq_status"] == "eligible_unmapped"

    def test_news_effective_weight_ineligible_host(self):
        """Test host excluded by eligible_news_hosts allow-list."""
        weight, meta = news_effective_weight("HostA", eligible_news_hosts=["HostB"])
        assert weight == 0.0
        assert meta["dq_status"] == "ineligible"

    def test_apply_news_dq(self):
        """Test apply_news_dq annotates documents without altering sentiment."""
        docs = [
            {"Host": "Bloomberg", "Sentiment": 0.8},
            {"Host": "Unknown Host", "Sentiment": -0.5},
        ]
        result = apply_news_dq(docs)
        assert len(result) == 2
        assert result[0]["Sentiment"] == 0.8
        assert result[0]["dq_weight"] == 3.0
        assert result[0]["dq_filtered"] is False
        assert result[1]["dq_weight"] == 1.0


class TestRedditDQ:
    def test_reddit_dq_weight_zones(self):
        """Test r/WSB dead, normal, and amplification zones."""
        assert reddit_dq_weight(None) == 0.0
        assert reddit_dq_weight(0.10) == 0.0
        assert reddit_dq_weight(0.20) == 0.0
        assert reddit_dq_weight(0.50) == 1.0
        assert reddit_dq_weight(0.60) == 1.0

        # Amplification zone (> 0.60): 1.0 + 5.0 * ((score - 0.60) / 0.40)^2
        score = 0.80
        expected = 1.0 + 5.0 * (((0.80 - 0.60) / 0.40) ** 2)
        assert pytest.approx(reddit_dq_weight(score), rel=1e-4) == expected

    def test_apply_reddit_dq_missing_fields(self):
        """Test r/WSB docs with missing required fields get marked missing."""
        docs = [{"title": "Post without karma or score"}]
        result = apply_reddit_dq(docs)
        assert result[0]["dq_status"] == "missing_required_fields"
        assert result[0]["dq_filtered"] is True
        assert result[0]["dq_weight"] == 0.0

    def test_apply_reddit_dq_valid_docs(self):
        """Test r/WSB doc batch scoring and min-max normalization."""
        docs = [
            {
                "stickied": False,
                "author_premium": True,
                "author_total_karma": 5000,
                "total_awards_received": 10,
                "Score": 100,
                "distinguished": "admin",
            },
            {
                "stickied": False,
                "author_premium": False,
                "author_total_karma": 100,
                "total_awards_received": 0,
                "Score": 10,
                "distinguished": None,
            },
        ]
        result = apply_reddit_dq(docs)
        assert len(result) == 2
        assert "DQ" in result[0]
        assert "dq_weight" in result[0]
        assert result[0]["credibility"] > result[1]["credibility"]


class TestDQHelpers:
    def test_effective_buzz(self):
        docs = [{"dq_weight": 1.8}, {"dq_weight": 3.0}, {"dq_weight": 0.0}]
        assert effective_buzz(docs) == 4.8

    def test_percentage_change(self):
        assert percentage_change(150, 100) == 50.0
        assert percentage_change(50, 100) == -50.0
        assert percentage_change(100, 0) == 0.0


# ============================================================================
# 2. Dual-Output & Suppression Tests (SentimentAlerts & SentimentPriceAlerts)
# ============================================================================

def _build_mock_daily_graph_responses(social_buzz_change=150, sentiment_change=30, social_buzz=10, news_buzz=10):
    """Build mock graph responses for SentimentAlerts."""
    stock = stock_list[0]
    return {
        graph_types[0]: [
            {"fields": "one_day_st_change_percent", stock: social_buzz_change},
            {"fields": "one_day_news_change_percent", stock: social_buzz_change},
        ],
        graph_types[1]: [
            {"fields": "one_day_st_change_percent", stock: sentiment_change},
            {"fields": "one_day_news_change_percent", stock: sentiment_change},
        ],
        graph_types[2]: [
            {"fields": "one_day_st", stock: 0.5},
            {"fields": "one_day_news", stock: 0.5},
        ],
        graph_types[3]: [
            {"fields": "one_day_st", stock: social_buzz},
            {"fields": "one_day_news", stock: news_buzz},
        ],
    }


class TestSentimentAlertsDualOutput:
    def test_generate_pre_market_alerts_structure(self):
        """Verify generate_pre_market_alerts returns dual output keys."""
        mock_responses = _build_mock_daily_graph_responses(
            social_buzz_change=150, sentiment_change=30, social_buzz=10, news_buzz=10
        )
        conditions = [
            {"sentiment_change": 25, "buzz_change": 50, "result": "BUY"}
        ]
        alerts = SentimentAlerts(
            only_faang=False, date="2025-06-17", page=1, conditions=conditions, daily_graph_api_responses=mock_responses
        )
        res = alerts.generate_pre_market_alerts()

        assert "alerts" in res
        assert "meta" in res
        assert "dq_alerts" in res
        assert "dq_meta" in res

        assert isinstance(res["alerts"], list)
        assert isinstance(res["meta"], list)
        assert isinstance(res["dq_alerts"], list)
        assert isinstance(res["dq_meta"], list)

        # Check non-DQ alert triggered
        assert len(res["alerts"]) == 1
        assert res["alerts"][0]["stock"] == stock_list[0]

        # Check DQ alert triggered
        assert len(res["dq_alerts"]) == 1
        assert res["dq_alerts"][0]["stock"] == stock_list[0]

    def test_dq_suppression_gate(self):
        """Verify DQ daily alerts are suppressed when combined DQ buzz < 8."""
        # Low buzz: news=1, social=1 -> combined_buzz = 2 (< 8)
        mock_responses = _build_mock_daily_graph_responses(
            social_buzz_change=150, sentiment_change=30, social_buzz=1, news_buzz=1
        )
        conditions = [
            {"sentiment_change": 25, "buzz_change": 50, "result": "BUY"}
        ]
        alerts = SentimentAlerts(
            only_faang=False, date="2025-06-17", page=1, conditions=conditions, daily_graph_api_responses=mock_responses
        )
        res = alerts.generate_pre_market_alerts()

        # Both non-DQ and DQ should be suppressed due to combined buzz < 8
        assert len(res["alerts"]) == 0
        assert len(res["dq_alerts"]) == 0
        assert res["meta"][0]["suppressed"] is True
        assert res["dq_meta"][0]["dq_suppressed"] is True


class TestSentimentPriceAlertsDualOutput:
    def test_non_trading_day_returns_empty_dual_lists(self, monkeypatch):
        """Verify non-trading day returns empty lists for all four keys."""
        mock_responses = _build_mock_daily_graph_responses()
        conditions = [
            {"sentiment_change": 25, "buzz_change": 50, "price_change": 1, "result": "BUY"}
        ]

        # Force is_trading_day to False
        monkeypatch.setattr("utils.AlertUtils.is_trading_day", lambda self, date: False)

        alerts = SentimentPriceAlerts(
            only_faang=False, date="2025-06-15T00:00:00+00:00", page=1, conditions=conditions, daily_graph_api_responses=mock_responses
        )
        res = alerts.generate_pre_market_alerts()

        assert res == {"alerts": [], "meta": [], "dq_alerts": [], "dq_meta": []}
