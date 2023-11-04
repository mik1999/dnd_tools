import telebot.handler_backends as telebot_backends


class BotStates(telebot_backends.StatesGroup):
    main = telebot_backends.State()
    dices = telebot_backends.State()
    alchemy = telebot_backends.State()
    alchemy_doc = telebot_backends.State()
    parameters = telebot_backends.State()
    dummy = telebot_backends.State()

    components_menu = telebot_backends.State()
    components_enter_name = telebot_backends.State()
    components_component_show = telebot_backends.State()
    components_location_choice = telebot_backends.State()
    components_enter_roll_value = telebot_backends.State()

    potions_menu = telebot_backends.State()
    potions_enter_formula = telebot_backends.State()
    potions_cooked = telebot_backends.State()
    potions_enter_name = telebot_backends.State()
    potions_list = telebot_backends.State()
    potion_show = telebot_backends.State()
    potions_cooking_doc = telebot_backends.State()
    potions_delete_confirm = telebot_backends.State()
    potions_common_potions_list = telebot_backends.State()
    potions_common_potion_show = telebot_backends.State()

    generators_menu = telebot_backends.State()
    names_generator = telebot_backends.State()
    names_generator_sex_choice = telebot_backends.State()
    names_generator_result = telebot_backends.State()
    treasury_generator = telebot_backends.State()

    bestiary_menu = telebot_backends.State()
    bestiary_enter_name = telebot_backends.State()
    bestiary_monster_info = telebot_backends.State()
    bestiary_monster_attacks = telebot_backends.State()

    npc_start_menu = telebot_backends.State()
    npc_create_race = telebot_backends.State()
    npc_create_gender = telebot_backends.State()
    npc_create_age = telebot_backends.State()
    npc_create_name = telebot_backends.State()
    npc_edit = telebot_backends.State()
    npc_edit_interaction = telebot_backends.State()
    npc_search = telebot_backends.State()
    npc_view = telebot_backends.State()
    npc_remove_note = telebot_backends.State()
    npc_remove_npc = telebot_backends.State()
    npc_edit_appearance = telebot_backends.State()
    npc_edit_race = telebot_backends.State()
    npc_edit_gender = telebot_backends.State()
    npc_edit_name = telebot_backends.State()
    npc_edit_features = telebot_backends.State()
    npc_edit_age = telebot_backends.State()
    npc_chat = telebot_backends.State()
    npc_edit_interaction_features = telebot_backends.State()
    npc_edit_interaction_manners = telebot_backends.State()

STATE_BY_COMMAND = {
    '/start': BotStates.main,
    '/dices': BotStates.dices,
    '/cook': BotStates.potions_enter_formula,
    '/name': BotStates.names_generator,
    '/bestiary': BotStates.bestiary_menu,
}
