from telegram.ext import ContextTypes

from internal.storage.preset_repository import UserSignalPresetRepository
from internal.telegram import texts, ui
from internal.telegram.auth import AuthService
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import (
    PRESET_CREATE_FILTERS,
    PRESET_CREATE_NAME,
    PRESET_CREATE_SIGNALS,
    PRESET_CREATE_TICK,
    SELECT_PRESETS,
)
from internal.telegram import options
from internal.telegram.steps import utils


def _build_preset_keyboard(
    repo: UserSignalPresetRepository,
    user_id: int,
    selected_ids: set[int],
    manage_only: bool,
):
    presets = repo.list_presets(user_id)
    if manage_only:
        return presets, ui.preset_manage_keyboard(presets)
    return presets, ui.preset_selection_keyboard(presets, selected_ids)


def make_signals_entry_handler(
    state_store: SessionStateStore,
    repo: UserSignalPresetRepository,
    auth_service: AuthService,
):
    async def handle_entry(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message
        if message is None:
            return SELECT_PRESETS
        user = update.effective_user
        if user is None or not auth_service.is_authorized(int(user.id)):
            await message.reply_text(
                "🚫 Доступ запрещён. Выполните /auth и отправьте токен.",
                reply_markup=ui.pair_keyboard(),
            )
            return SELECT_PRESETS

        state = state_store.reset(context)
        state.manage_presets_only = True
        state.pair_code = None
        state.selected_preset_ids = set()
        state_store.save(context, state)

        presets, keyboard = _build_preset_keyboard(
            repo,
            int(user.id),
            state.selected_preset_ids,
            True,
        )
        await message.reply_text(
            texts.PRESET_MENU_TITLE if presets else texts.PRESET_EMPTY,
            reply_markup=keyboard,
        )
        return SELECT_PRESETS

    return handle_entry


def make_preset_menu_handler(
    state_store: SessionStateStore,
    repo: UserSignalPresetRepository,
    auth_service: AuthService,
):
    async def handle_presets(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_PRESETS

        user = update.effective_user

        if user is None or not auth_service.is_authorized(int(user.id)):
            await message.reply_text(
                "🚫 Доступ запрещён. Выполните /auth и отправьте токен.",
                reply_markup=ui.pair_keyboard(),
            )
            return SELECT_PRESETS

        uid = int(user.id)
        text = message.text.strip()
        state = state_store.load(context)
        selected_ids = state.selected_preset_ids or set()
        manage_only = state.manage_presets_only

        if text == ui.KB_RESTART:
            state.selected_preset_ids = set()
            state.manage_presets_only = False
            state_store.save(context, state)
            await message.reply_text(
                texts.START_PAIR_PROMPT,
                reply_markup=ui.pair_keyboard(),
            )
            return SELECT_PRESETS

        if text == ui.KB_PRESET_ADD:
            state.preset_name = None
            state.preset_k_type = None
            state.preset_signals = set()
            state.preset_filters = set()
            state_store.save(context, state)
            await message.reply_text(texts.PRESET_ENTER_NAME)
            return PRESET_CREATE_NAME

        if text == ui.KB_PRESET_DONE:
            if manage_only:
                presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, True)
                await message.reply_text(
                    texts.PRESET_MENU_TITLE if presets else texts.PRESET_EMPTY,
                    reply_markup=keyboard,
                )
                return SELECT_PRESETS
            if not selected_ids:
                await message.reply_text(
                    texts.PRESET_NEED_SELECT,
                    reply_markup=ui.preset_selection_keyboard(
                        repo.list_presets(uid),
                        selected_ids,
                    ),
                )
                return SELECT_PRESETS
            state.selected_preset_ids = set(selected_ids)
            state_store.save(context, state)
            if not state.pair_code:
                await message.reply_text(
                    texts.NEED_PAIR_FIRST,
                    reply_markup=ui.pair_keyboard(),
                )
                return SELECT_PRESETS

            return await utils.start_monitoring_presets(
                update,
                context,
                state_store,
                repo,
                auth_service,
                state.pair_code,
                state.selected_preset_ids,
            )

        # удаление
        if text.startswith("🗑"):
            name = text.removeprefix("🗑").strip()
            if not manage_only:
                presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, manage_only)
                await message.reply_text(
                    texts.PRESET_SELECT_FOR_MONITOR,
                    reply_markup=keyboard,
                )
                return SELECT_PRESETS
            repo.delete_preset(uid, name)
            presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, manage_only)
            await message.reply_text(
                texts.PRESET_DELETED,
                reply_markup=keyboard,
            )
            return SELECT_PRESETS

        # toggle select
        if (text.startswith("✓") or text.startswith("◻")) and not manage_only:
            name_part = text[1:].strip()
            presets = repo.list_presets(uid)
            found = next((p for p in presets if f"{p['name']} (TF {p['k_type']})" == name_part), None)
            if found is None:
                # try by name only
                found = next((p for p in presets if p["name"] == name_part.split(" (TF")[0]), None)
            if found is not None:
                pid = int(found["id"])
                if pid in selected_ids:
                    selected_ids.discard(pid)
                else:
                    selected_ids.add(pid)
                state.selected_preset_ids = set(selected_ids)
                state_store.save(context, state)
            presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, manage_only)
            await message.reply_text(
                texts.PRESET_SELECT_FOR_MONITOR,
                reply_markup=keyboard,
            )
            return SELECT_PRESETS

        # если текст совпадает с именем пресета — toggle
        presets = repo.list_presets(uid)
        found = next((p for p in presets if p["name"] == text), None)
        if found and not manage_only:
            pid = int(found["id"])
            if pid in selected_ids:
                selected_ids.discard(pid)
            else:
                selected_ids.add(pid)
            state.selected_preset_ids = set(selected_ids)
            state_store.save(context, state)
            presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, manage_only)
            await message.reply_text(
                texts.PRESET_SELECT_FOR_MONITOR,
                reply_markup=keyboard,
            )
            return SELECT_PRESETS

        # неизвестный ввод
        presets, keyboard = _build_preset_keyboard(repo, uid, selected_ids, manage_only)
        await message.reply_text(
            texts.PRESET_MENU_TITLE if manage_only else texts.PRESET_SELECT_FOR_MONITOR,
            reply_markup=keyboard,
        )
        return SELECT_PRESETS

    return handle_presets


def make_preset_create_name_handler(state_store: SessionStateStore, repo: UserSignalPresetRepository):
    async def handle_name(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return PRESET_CREATE_NAME

        text = message.text.strip()

        if not text:
            await message.reply_text(texts.PRESET_NAME_EMPTY)
            return PRESET_CREATE_NAME

        state = state_store.load(context)
        state.preset_name = text
        state_store.save(context, state)

        await message.reply_text(
            texts.SELECT_TICK_PROMPT,
            reply_markup=ui.tick_keyboard(),
        )
        return PRESET_CREATE_TICK

    return handle_name


def make_preset_create_tick_handler(state_store: SessionStateStore):
    async def handle_tick(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return PRESET_CREATE_TICK

        text = message.text.strip()
        k_type = options.find_tick_value(text)

        if k_type is None:
            await message.reply_text(
                texts.INVALID_TICK_PROMPT,
                reply_markup=ui.tick_keyboard(),
            )
            return PRESET_CREATE_TICK

        state = state_store.load(context)
        state.preset_k_type = k_type
        state.preset_signals = set()
        state.preset_filters = set()
        state_store.save(context, state)

        await message.reply_text(
            texts.SELECT_SIGNAL_PROMPT.format(
                select_all=ui.KB_SIGNAL_SELECT_ALL,
                done=ui.KB_SIGNAL_DONE,
            ),
            reply_markup=ui.signal_selection_keyboard(set()),
        )
        return PRESET_CREATE_SIGNALS

    return handle_tick


def make_preset_create_signals_handler(state_store: SessionStateStore):
    async def handle_signals(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return PRESET_CREATE_SIGNALS

        text_raw = message.text.strip()
        text = options.normalize_option_label(text_raw)
        state = state_store.load(context)
        selected = state.preset_signals or set()

        if text == ui.KB_SIGNAL_SELECT_ALL:
            for item in options.DEFAULT_SIGNAL_OPTIONS:
                selected.add(item["value"])
            state.preset_signals = set(selected)
            state_store.save(context, state)
            await message.reply_text(
                f"Выбрано всё. Сейчас: {options.summarize_signal_keys(selected)}",
                reply_markup=ui.signal_selection_keyboard(selected),
            )
            return PRESET_CREATE_SIGNALS

        if text == ui.KB_SIGNAL_DONE:
            if not selected:
                await message.reply_text(
                    texts.PRESET_NEED_SIGNAL,
                    reply_markup=ui.signal_selection_keyboard(selected),
                )
                return PRESET_CREATE_SIGNALS

            state.preset_signals = set(selected)
            state.preset_filters = set()
            state_store.save(context, state)

            await message.reply_text(
                texts.SELECT_FILTER_PROMPT.format(
                    select_all=ui.KB_SIGNAL_SELECT_ALL,
                    done=ui.KB_SIGNAL_DONE,
                ),
                reply_markup=ui.filter_selection_keyboard(set()),
            )
            return PRESET_CREATE_FILTERS

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
            return PRESET_CREATE_SIGNALS

        state.preset_signals = set(selected)
        state_store.save(context, state)

        await message.reply_text(
            f"Сейчас: {options.summarize_signal_keys(selected)}",
            reply_markup=ui.signal_selection_keyboard(selected),
        )
        return PRESET_CREATE_SIGNALS

    return handle_signals


def make_preset_create_filters_handler(state_store: SessionStateStore, repo: UserSignalPresetRepository):
    async def handle_filters(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return PRESET_CREATE_FILTERS

        text_raw = message.text.strip()
        text = options.normalize_option_label(text_raw)
        state = state_store.load(context)
        selected_filters = state.preset_filters or set()
        manage_only = state.manage_presets_only

        if text == ui.KB_SIGNAL_SELECT_ALL:
            for item in options.DEFAULT_FILTER_OPTIONS:
                selected_filters.add(item["value"])
            state.preset_filters = set(selected_filters)
            state_store.save(context, state)
            await message.reply_text(
                f"Выбрано всё. Сейчас: {options.summarize_filter_keys(selected_filters)}",
                reply_markup=ui.filter_selection_keyboard(selected_filters),
            )
            return PRESET_CREATE_FILTERS

        if text == ui.KB_SIGNAL_DONE:
            state.preset_filters = set(selected_filters)
            state_store.save(context, state)

            user = update.effective_user
            if user is None:
                await message.reply_text(texts.PRESET_NAME_EMPTY)
                return SELECT_PRESETS

            uid = int(user.id)
            try:
                repo.upsert_preset(
                    telegram_user_id=uid,
                    name=state.preset_name or "",
                    k_type=int(state.preset_k_type or 1),
                    signal_ids=list(state.preset_signals or []),
                    filter_ids=list(state.preset_filters or []),
                )
                state.preset_name = None
                state.preset_k_type = None
                state.preset_signals = set()
                state.preset_filters = set()
                state_store.save(context, state)
                if manage_only:
                    await message.reply_text(
                        texts.PRESET_SAVED,
                        reply_markup=ui.preset_manage_keyboard(
                            repo.list_presets(uid),
                        ),
                    )
                else:
                    await message.reply_text(
                        texts.PRESET_SAVED,
                        reply_markup=ui.preset_selection_keyboard(
                            repo.list_presets(uid),
                            state.selected_preset_ids or set(),
                        ),
                    )
                return SELECT_PRESETS
            except Exception as exc:
                await message.reply_text(
                    texts.SCRIPT_FAILED.format(error=exc),
                    reply_markup=ui.filter_selection_keyboard(selected_filters),
                )
                return PRESET_CREATE_FILTERS

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
            return PRESET_CREATE_FILTERS

        state.preset_filters = set(selected_filters)
        state_store.save(context, state)

        await message.reply_text(
            f"Сейчас: {options.summarize_filter_keys(selected_filters)}",
            reply_markup=ui.filter_selection_keyboard(selected_filters),
        )
        return PRESET_CREATE_FILTERS

    return handle_filters
