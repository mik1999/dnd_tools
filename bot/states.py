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

    potions_menu = telebot_backends.State()
    potions_enter_formula = telebot_backends.State()
    potions_cooked = telebot_backends.State()
    potions_enter_name = telebot_backends.State()
    potions_list = telebot_backends.State()
    potion_show = telebot_backends.State()
    potions_cooking_doc = telebot_backends.State()
    potions_delete_confirm = telebot_backends.State()

    generators_menu = telebot_backends.State()
    names_generator = telebot_backends.State()
    names_generator_sex_choice = telebot_backends.State()
    bestiary_menu = telebot_backends.State()
    bestiary_enter_name = telebot_backends.State()
    bestiary_monster_info = telebot_backends.State()
    bestiary_monster_attacks = telebot_backends.State()


STATE_BY_COMMAND = {
    '/start': BotStates.main,
    '/dices': BotStates.dices,
    '/cook': BotStates.potions_enter_formula,
    '/name': BotStates.names_generator,
    '/bestiary': BotStates.bestiary_menu,
}
