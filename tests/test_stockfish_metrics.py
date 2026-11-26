import json
import logging

from game import Game
from logging_config import JsonFormatter, bind_request_context, clear_request_context, setup_logging
from metrics import measure_skill_request


def test_engine_timings_are_visible_at_warning_without_request_logs(caplog):
    root_level = logging.getLogger().level
    try:
        setup_logging('WARNING')
        bind_request_context(user_id='private-account')
        with measure_skill_request('pilot'), measure_skill_request('legacy'), Game() as game:
            logging.getLogger('alice_chess').info('private-request-body')
            assert game.comp_move() == 'e4'
        with measure_skill_request('legacy'), Game() as game:
            game.get_board()
        for record in caplog.records:
            if hasattr(record, 'metric'):
                assert 'ctx' not in json.loads(JsonFormatter().format(record))
    finally:
        clear_request_context()
        setup_logging(logging.getLevelName(root_level))

    metric_records = [r for r in caplog.records if hasattr(r, 'metric')]
    assert [r.metric for r in metric_records].count('skill.request') == 2
    histograms = [r for r in metric_records if r.metric_kind == 'histogram']
    assert [r.metric for r in histograms] == [
        'skill.stockfish.startup_ms',
        'skill.stockfish.play_ms',
        'skill.handler.duration_ms',
        'skill.handler.duration_ms',
    ]
    assert [r.metric_tags for r in histograms[-2:]] == [
        {'entrypoint': 'pilot', 'engine': 'yes'},
        {'entrypoint': 'legacy', 'engine': 'no'},
    ]
    assert all(r.metric_value >= 0 for r in histograms)
    assert 'private-request-body' not in caplog.text
