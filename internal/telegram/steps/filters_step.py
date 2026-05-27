from telegram.ext import ContextTypes

from internal.telegram import options, texts, ui
from internal.telegram.state import SessionStateStore
from internal.telegram.steps import utils
from internal.telegram.steps.flow import MONITORING, SELECT_FILTERS, SELECT_SIGNALS


def make_filters_handler(state_store: SessionStateStore, restart_handler):
    async def handle_filters(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_FILTERS

        text_raw = message.text.strip()
        text = options.normalize_option_label(text_raw)
        state = state_store.load(context)
        pair_code = state.pair_code
        k_type = state.pending_k_type
        selected_signals = state.selected_signals or set()
        selected_filters = state.selected_filters or set()

        if not selected_signals:
            await message.reply_text(texts.NEED_PAIR_AND_TICK)

            return await restart_handler(update, context)

        if text == ui.KB_RESTART:
            state.selected_filters = set()
            state_store.save(context, state)

            await message.reply_text(
                f"Сейчас: {options.summarize_signal_keys(selected_signals)}",
                reply_markup=ui.signal_selection_keyboard(selected_signals),
            )

            return SELECT_SIGNALS

        if pair_code is None or k_type is None:
            await message.reply_text(texts.NEED_PAIR_AND_TICK)

            return await restart_handler(update, context)

        if text == ui.KB_SIGNAL_SELECT_ALL:
            for item in options.DEFAULT_FILTER_OPTIONS:
                selected_filters.add(item["value"])

            state.selected_filters = set(selected_filters)
            state_store.save(context, state)

            await message.reply_text(
                f"Выбрано всё. Сейчас: {options.summarize_filter_keys(selected_filters)}",
                reply_markup=ui.filter_selection_keyboard(selected_filters),
            )

            return SELECT_FILTERS

        if text == ui.KB_SIGNAL_DONE:
            state.selected_filters = set(selected_filters)
            state_store.save(context, state)

            return await utils.start_monitoring(
                update,
                context,
                state_store,
                pair_code,
                int(k_type),
                selected_signals,
                frozenset(selected_filters),
            )

        toggled = False

        for item in options.DEFAULT_FILTER_OPTIONS:
            if item["label"] == text:
                value = item["value"]

                if value in selected_filters:
                    selected_filters.discard(value)
                else:
                    selected_filters.add(value)

                toggled = True
                break

        if not toggled:
            await message.reply_text(
                texts.FILTER_BUTTONS_ONLY.format(
                    select_all=ui.KB_SIGNAL_SELECT_ALL,
                    done=ui.KB_SIGNAL_DONE,
                    restart=ui.KB_RESTART,
                ),
                reply_markup=ui.filter_selection_keyboard(selected_filters),
            )

            return SELECT_FILTERS

        state.selected_filters = set(selected_filters)
        state_store.save(context, state)

        await message.reply_text(
            f"Сейчас: {options.summarize_filter_keys(selected_filters)}",
            reply_markup=ui.filter_selection_keyboard(selected_filters),
        )

        return SELECT_FILTERS

    return handle_filters
