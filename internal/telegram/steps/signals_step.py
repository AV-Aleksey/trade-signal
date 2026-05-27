from telegram.ext import ContextTypes

from internal.telegram import options, texts, ui
from internal.telegram.state import SessionStateStore
from internal.telegram.steps import utils
from internal.telegram.steps.flow import MONITORING, SELECT_FILTERS, SELECT_SIGNALS, SELECT_TICK


def make_signals_handler(
    state_store: SessionStateStore,
    restart_handler,
    filters_enabled: bool,
    default_filter_keys: frozenset[str],
):
    async def handle_signals(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_SIGNALS

        text_raw = message.text.strip()
        text = options.normalize_option_label(text_raw)
        state = state_store.load(context)
        pair_code = state.pair_code
        k_type = state.pending_k_type
        selected = state.selected_signals or set()

        if text == ui.KB_RESTART:
            state.pending_k_type = None
            state.selected_signals = set()
            state.selected_filters = set()
            state_store.save(context, state)

            if pair_code is None:
                return await restart_handler(update, context)

            await message.reply_text(
                texts.SELECT_TICK_PROMPT,
                reply_markup=ui.tick_keyboard(),
            )

            return SELECT_TICK

        if pair_code is None or k_type is None:
            await message.reply_text(texts.NEED_PAIR_AND_TICK)

            return await restart_handler(update, context)

        if text == ui.KB_SIGNAL_SELECT_ALL:
            for item in options.DEFAULT_SIGNAL_OPTIONS:
                selected.add(item["value"])

            state.selected_signals = set(selected)
            state_store.save(context, state)

            await message.reply_text(
                f"Выбрано всё. Сейчас: {options.summarize_signal_keys(selected)}",
                reply_markup=ui.signal_selection_keyboard(selected),
            )

            return SELECT_SIGNALS

        if text == ui.KB_SIGNAL_DONE:
            if not selected:
                await message.reply_text(
                    texts.SIGNAL_NEED_AT_LEAST_ONE.format(
                        select_all=ui.KB_SIGNAL_SELECT_ALL,
                    ),
                    reply_markup=ui.signal_selection_keyboard(selected),
                )

                return SELECT_SIGNALS

            if not filters_enabled:
                state.selected_filters = set(default_filter_keys)
                state_store.save(context, state)

                return await utils.start_monitoring(
                    update,
                    context,
                    state_store,
                    pair_code,
                    int(k_type),
                    selected,
                    frozenset(default_filter_keys),
                )

            await message.reply_text(
                texts.SELECT_FILTER_PROMPT.format(
                    select_all=ui.KB_SIGNAL_SELECT_ALL,
                    done=ui.KB_SIGNAL_DONE,
                ),
                reply_markup=ui.filter_selection_keyboard(set()),
            )

            state.selected_filters = set()
            state_store.save(context, state)

            return SELECT_FILTERS

        toggled = False

        for item in options.DEFAULT_SIGNAL_OPTIONS:
            if item["label"] == text:
                value = item["value"]

                if value in selected:
                    selected.discard(value)
                else:
                    selected.add(value)

                toggled = True
                break

        if not toggled:
            await message.reply_text(
                texts.SIGNAL_BUTTONS_ONLY.format(
                    select_all=ui.KB_SIGNAL_SELECT_ALL,
                    done=ui.KB_SIGNAL_DONE,
                    restart=ui.KB_RESTART,
                ),
                reply_markup=ui.signal_selection_keyboard(selected),
            )

            return SELECT_SIGNALS

        state.selected_signals = set(selected)
        state_store.save(context, state)

        await message.reply_text(
            f"Сейчас: {options.summarize_signal_keys(selected)}",
            reply_markup=ui.signal_selection_keyboard(selected),
        )

        return SELECT_SIGNALS

    return handle_signals
