import abc
import copy
import datetime
import math
import random
import uuid

import numpy

import generators
import resources_manager
import helpers

import pymongo
import pymongo.errors as mongo_errors
import telebot.types

import messages as msgs
import typing
from states import BotStates

from base_handler import BaseMessageHandler, DocHandler
from utils import consts
import yandex_gpt
from npc_utils import NpcMessageHandler


EVERYDAY_COINS = 100


def suggest_bet(user_coins: int):
    if user_coins <= 3:
        return 1
    if user_coins <= 5:
        return 2
    log_10 = math.log10(user_coins)
    rest = log_10 - int(log_10)
    if rest >= 0.78: # log(6)
        multiplier = 2
    elif rest >= 0.48: # log(3)
        multiplier = 1
    else:
        multiplier = 0.5
    return int((10 ** int(log_10)) * multiplier)


def pretty_list(items: typing.List[str]) -> str:
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    return ', '.join(items[:-1]) + ' и ' + items[-1]


class CasinoMainHandler(BaseMessageHandler):
    STATE = BotStates.casino_main
    STATE_BY_MESSAGE = {
        'Двадцать одно': {'state': BotStates.casino_twenty_one_start},
        'Назад': {'state': BotStates.main},
    }
    PARSE_MODE = 'MarkdownV2'

    BUTTONS = [['Двадцать одно'], ['Назад']]

    def get_default_message(self):
        user_info = self.mongo.user_info.find_one({'user': self.message.from_user.id})
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        if (
            not user_info
            or not user_info.get('last_coins_raise')
            or (
                user_info['last_coins_raise'].strftime('%Y-%m-%d') < current_date
                and user_info['coins'] < EVERYDAY_COINS
            )
        ):
            coins = EVERYDAY_COINS
            self.mongo.user_info.update_one(
                {'user': self.message.from_user.id},
                {
                    '$set': {
                        'last_coins_raise': datetime.datetime.now(),
                        'coins': coins,
                    },
                },
                upsert=True,
            )
            return msgs.CASINO_RAISE.format(coins)

        coins = user_info['coins']
        if coins <= 0:
            return msgs.CASINO_NO_COINS
        return msgs.CASINO_BALANCE.format(coins)

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        user = self.mongo.user_info.find_one(
            {'user': message.from_user.id},
            {'coins': 1},
        )
        if user['coins'] <= 0:
            return self.switch_to_state(BotStates.main, 'Сказано же: у вас кончились золотые) Приходите завтра')
        return self.process_state_by_message(unknown_pass_enabled=False)


TWENTY_ONE_DICES = [20, 12, 10, 8, 6, 4]
TWENTY_ONE_DICES_STR = {f'd{d}' for d in TWENTY_ONE_DICES}


class BaseStrategy:
    @staticmethod
    @abc.abstractmethod
    def play() -> typing.Tuple[typing.List[str], typing.List[int]]:
        """
        :return: list if dices, list of realizations
        """


class GreedyStrategy(BaseStrategy):
    # maximize expected dices sum (>21 is treated as 0)
    @staticmethod
    def play() -> typing.Tuple[typing.List[str], typing.List[int]]:
        rest_dices = set(TWENTY_ONE_DICES)
        current_sum = 0
        dices = []
        realizations = []
        for _ in range(6):
            max_expected_sum = float(current_sum)
            dice_that_maximize = None
            for dice in rest_dices:
                if current_sum + dice <= 21:
                    expected_sum = current_sum + (dice / 2 + 0.5)
                else:
                    sub_dice = 21 - current_sum
                    expected_sum = (current_sum + (sub_dice / 2 + 0.5)) * (sub_dice / dice)
                if expected_sum > max_expected_sum:
                    max_expected_sum = expected_sum
                    dice_that_maximize = dice
            if dice_that_maximize:
                dices.append(f'd{dice_that_maximize}')
                rest_dices.remove(dice_that_maximize)
                realization = random.randint(1, dice_that_maximize)
                realizations.append(realization)
                if sum(realizations) >= 21:
                    break
            else:
                break
        return dices, realizations


STRATEGIES = {
    'greedy': GreedyStrategy,
}


class CommonTwentyOneStartHandler(BaseMessageHandler):
    STATE_BY_MESSAGE = {
        'Играть!': {'state': BotStates.casino_twenty_one_step_1},
        'Правила': {'state': BotStates.casino_twenty_one_info},
        'Предложить ставку': {'state': BotStates.casino_twenty_one_change_bet},
        'Уйти': {'state': BotStates.casino_main},
    }

    BUTTONS = [['Играть!'], ['Правила', 'Предложить ставку', 'Уйти']]

    def generate_players(self, user_coins):
        expected_bet = suggest_bet(user_coins)
        num_players = random.randint(0, 2) + random.randint(0, 2) + 1
        return [
            {
                'id': i,
                'name': self.gm.sample_name().name,
                'coins': expected_bet * (1 + numpy.random.poisson(9)),
                'strategy': 'greedy',
            }
            for i in range(num_players)
        ]

    @abc.abstractmethod
    def make_game(self) -> dict:
        ...

    def get_default_message(self):
        game = self.make_game()
        players = game['players']
        if len(players) == 1:
            about_round = 'ожидающий(-ая) компании для игры' if game['round'] == 1 else 'желающий(-ая) продолжить игру'
            about_players = 'За столом одиноко сидит {}, {} в Двадцать одно'.format(players[0]['name'], about_round)
        else:
            players_joined = pretty_list([p['name'] for p in players])
            about_round = 'приглашают вас присоединиться' if game['round'] == 1 else 'хотят продолжить игру'
            about_players = 'За столом играют {}. Они {}'.format(players_joined, about_round)
        return f'{about_players}\nТекущая ставка {game["bet"]} зм. У вас в наличие {game["user_coins"]} зм.'


class TwentyOneStartHandler(CommonTwentyOneStartHandler):
    STATE = BotStates.casino_twenty_one_start

    def make_game(self) -> dict:
        user_coins = self.mongo.user_info.find_one({'user': self.message.from_user.id}, {'coins': 1})['coins']
        game_id = uuid.uuid4().hex
        players = self.generate_players(user_coins)
        bet = suggest_bet(user_coins)
        game = {
            '_id': game_id,
            'user': self.message.from_user.id,
            'user_coins': user_coins,
            'bet': bet,
            'players': players,
            'created': datetime.datetime.now(),
            'status': 'init',
            'rest_dices': TWENTY_ONE_DICES,
            'dices_chosen': [],
            'dices_realization': [],
            'round': 1,
        }
        self.mongo.games.insert_one(game)
        self.set_user_cache(game_id)
        return game


class TwentyOneRestartHandler(CommonTwentyOneStartHandler):
    STATE = BotStates.casino_twenty_one_restart

    def make_game(self) -> dict:
        game_id = self.get_user_cache()
        return self.mongo.games.find_one({'_id': game_id})


class TwentyOneDoc(DocHandler):
    STATE = BotStates.casino_twenty_one_info
    PARENT_STATE = BotStates.casino_twenty_one_restart
    DEFAULT_MESSAGE = msgs.TWENTY_ONE_INFO


class TwentyOneChangeBetHandler(BaseMessageHandler):
    STATE = BotStates.casino_twenty_one_change_bet
    DEFAULT_MESSAGE = 'Какую ставку вы хотите предложить? Можете выбрать вариант или ввести свой'

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        user_coins = game['user_coins']
        bet = game['bet']
        bets_to_suggest = []
        if bet >= 10:
            bets_to_suggest.append(bet // 10)
        if bet >= 5:
            bets_to_suggest.append(bet // 5)
        if bet >= 2:
            bets_to_suggest.append(bet // 2)
        if bet * 2 <= user_coins:
            bets_to_suggest.append(bet * 2)
        if bet * 5 <= user_coins:
            bets_to_suggest.append(bet * 5)
        if bet * 10 <= user_coins:
            bets_to_suggest.append(bet * 10)
        same_bet = 'Оставить ' + str(bet)
        if len(bets_to_suggest) < 5:
            return [
                [same_bet],
                [str(bet) for bet in bets_to_suggest],
            ]
        return [
            [same_bet],
            [str(bet) for bet in bets_to_suggest[:3]],
            [str(bet) for bet in bets_to_suggest[3:]],
        ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text.startswith('Оставить'):
            return self.switch_to_state(BotStates.casino_twenty_one_restart)
        try:
            bet = int(message.text)
        except ValueError:
            return self.try_again(msgs.NOT_A_NUMBER_ENTERED)
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        user_coins = game['user_coins']
        if bet > user_coins:
            return self.try_again(f'У вас осталось только {bet} зм, вы не можете предлагать ставку больше этой суммы')
        players_leaved = []
        rest_players = []
        for player in game['players']:
            if player['coins'] < bet:
                players_leaved.append(player)
            else:
                rest_players.append(player)
        if players_leaved:
            self.send_message(pretty_list([p['name'] for p in players_leaved]) + ' больше не играют(-ет) с вами')
        if not rest_players:
            return self.switch_to_state(BotStates.casino_main, 'Никто из игроков не смог поддержать такую ставку. Вам придется искать новую компанию')
        self.mongo.games.update_one(
            {'_id': game_id},
            {
                '$set': {
                    'bet': bet,
                    'players': rest_players,
                },
            },
        )
        return self.switch_to_state(BotStates.casino_twenty_one_restart)


class TwentyOneStep1Handler(BaseMessageHandler):
    STATE = BotStates.casino_twenty_one_step_1
    DEFAULT_MESSAGE = 'Выберите первую кость'

    BUTTONS = [['d20', 'd12', 'd10'], ['d8', 'd6', 'd4']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text not in TWENTY_ONE_DICES_STR:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        # сразу спишем у юзера деньги, чтобы не мухлевал
        self.mongo.user_info.update_one(
            {'user': message.from_user.id},
            {
                '$set': {
                    'coins': game['user_coins'] - game['bet'],
                }
            },
        )


        chosen_dice = int(message.text[1:])
        rest_dices = copy.deepcopy(TWENTY_ONE_DICES)
        rest_dices.pop(rest_dices.index(chosen_dice))
        self.mongo.games.update_one(
            {'_id': game_id},
            {
                '$set': {
                    'dices_chosen': [chosen_dice],
                    'rest_dices': rest_dices,
                    'status': 'in_progress',
                }
            }
        )
        return self.switch_to_state(BotStates.casino_twenty_one_step_2)


class BaseFinalState(BaseMessageHandler):
    def handle_final(self, game: dict) -> telebot.types.Message:
        final_message = ''
        dices_realization = game['dices_realization']
        if sum(dices_realization) == 21:
            final_message += 'Блэкджек! '
        final_message += 'Ваш результат {} = {}.'.format(' + '.join([str(d) for d in dices_realization]), sum(dices_realization))
        if sum(dices_realization) > 21:
            final_message += ' Перебор!'
        final_message += '\nРезультаты бросков других игроков:\n'
        players_results = {'user': sum(dices_realization)}
        for player in game['players']:
            strategy = STRATEGIES[player['strategy']]
            dices, realizations = strategy().play()
            player_sum = sum(realizations)
            players_results.update({player['id']: player_sum})
            extra_comment = ''
            if player_sum == 21:
                extra_comment = ' Блэкджек!'
            if player_sum > 21:
                extra_comment = ' Перебор!'
            final_message += '{} кидал(-а) {}. Выпало {} = {}.{}\n'.format(
                player['name'],
                pretty_list(dices),
                ' + '.join([str(r) for r in realizations]),
                sum(realizations),
                extra_comment,
            )
        max_result = -1
        for player_result in players_results.values():
            if player_result <= 21:
                max_result = max(max_result, player_result)
        win_players = []
        for id, player_result in players_results.items():
            if player_result == max_result:
                win_players.append(id)
        if all([result > 21 for result in players_results.values()]):
            # Все остались при своем
            user_coins_to_be = game['user_coins']
            final_message += 'Перебор у всех игроков! Каждый остался при своём'
        else:
            win_sum = (1 + len(game['players'])) * game['bet']
            win_value = win_sum // len(win_players)
            rest = win_sum % len(win_players)
            if 'user' in win_players:
                final_message += f'Вы выиграли {win_value} зм.'
                user_coins_to_be = game['user_coins'] + win_value
            else:
                final_message += f'Вы проиграли {game["bet"]} зм.'
                user_coins_to_be = game['user_coins'] - game['bet']
            if rest:
                final_message += f' Также {rest} зм не смогли поделить и раздали беднякам'

            for player in game['players']:
                if player['id'] in win_players:
                    player['coins'] += win_value
                else:
                    player['coins'] -= game['bet']

        self.send_message(final_message)

        players_leaved = []
        rest_players = []
        for player in game['players']:
            if player['coins'] < game['bet']:
                players_leaved.append(player)
            else:
                rest_players.append(player)
        if players_leaved:
            self.send_message(
                pretty_list([p['name'] for p in players_leaved]) + ' больше не могут поддерживать ставку и покидают игру',
            )
        self.mongo.user_info.update_one(
            {'user': self.message.from_user.id},
            {
                '$set': {'coins': user_coins_to_be},
            }
        )
        self.mongo.games.update_one(
            {'_id': game['_id']},
            {
                '$set': {
                    'players': rest_players,
                    'user_coins': user_coins_to_be,
                    'status': 'finished',
                    'round': game['round'] + 1,
                    'rest_dices': TWENTY_ONE_DICES,
                    'dices_chosen': [],
                    'dices_realization': [],
                }
            }
        )

        if not rest_players:
            return self.switch_to_state(BotStates.casino_main, 'Вы победили всех за этим столом! Больше никто не может поддерживать ставку')
        return self.switch_to_state(BotStates.casino_twenty_one_restart)

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        if message.text == 'Хватит' and len(game['dices_chosen']) >= 2:
            return self.handle_final(game)
        try:
            dice_chosen = int(message.text[1:])
        except ValueError:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)

        rest_dices = game['rest_dices']
        if dice_chosen not in rest_dices:
            return self.try_again('Нельзя дважды выбирать одну и ту же кость')

        dices_chosen = game['dices_chosen'] + [dice_chosen]
        dices_realization = game['dices_realization']
        for i in range(len(game['dices_realization']), len(dices_chosen)):
            dices_realization.append(random.randint(1, dices_chosen[i]))

        rest_dices.pop(rest_dices.index(dice_chosen))

        if sum(dices_realization) >= 21 or not rest_dices:
            game['dices_chosen'] += [dice_chosen]
            game['dices_realization'] = dices_realization
            # game['rest_dices'] updated above
            return self.handle_final(game)
        self.mongo.games.update_one(
            {'_id': game_id},
            {
                '$set': {
                    'dices_chosen': game['dices_chosen'] + [dice_chosen],
                    'dices_realization': dices_realization,
                    'rest_dices': rest_dices,
                }
            }
        )
        message = 'Вы выбрали кости {}. Сумма {} = {}. Ещё одну кость?'.format(
            pretty_list([f'd{d}' for d in dices_chosen]),
            ' + '.join([str(d) for d in dices_realization]),
            sum(dices_realization),
        )
        return self.switch_to_state(BotStates.casino_twenty_one_other_steps, message=message)

class TwentyOneStep2Handler(BaseFinalState):
    STATE = BotStates.casino_twenty_one_step_2
    DEFAULT_MESSAGE = 'Выберите вторую кость'

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        rest_dices = [f'd{d}' for d in game['rest_dices']]
        if game['dices_chosen'] in [20, 12, 10]:
            return [
                rest_dices[:2],
                rest_dices[2:],
            ]
        return [
            rest_dices[:3],
            rest_dices[3:],
        ]


class TwentyOneOtherStepsHandler(BaseFinalState):
    STATE = BotStates.casino_twenty_one_other_steps

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        game_id = self.get_user_cache()
        game = self.mongo.games.find_one({'_id': game_id})
        return [[f'd{d}' for d in game['rest_dices']], ['Хватит']]
