import random
from playcard import make_deck

# from userlog import add_log_entry

CARD_VALUES = {
    'A': 11,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'T': 10,
    'J': 10,
    'Q': 10,
    'K': 10,
}


def calculate_hand_value(hand):
    # Calculate the value of a hand, considering Aces as 1 or 11.
    value, aces = 0, 0
    for card in hand:
        rank = card[0]
        value += CARD_VALUES[rank]
        aces += rank == 'A'

    # Adjust for Aces if needed
    while value > 21 and aces:
        value -= 10
        aces -= 1

    return value


def is_natural_blackjack(hand):
    """检查手牌是否为自然Blackjack（仅由最初的两张牌组成：A + 10点牌）"""
    if len(hand) != 2:
        return False
    ranks = [card[0] for card in hand]
    return ('A' in ranks) and any(rank in ['T', 'J', 'Q', 'K'] for rank in ranks)


def new_game(session):
    # Create a standard deck of 52 cards
    session_id = session.get('session_id', '')
    deck = make_deck()
    random.shuffle(deck)
    # 欧式规则：只发3张牌。玩家2张，庄家1张明牌。
    card1, card2, card3 = deck.pop(), deck.pop(), deck.pop()
    player_hand = [card1, card3]
    dealer_hand = [card2]  # 庄家初始只有一张明牌
    # 计算初始点数
    player_value = calculate_hand_value(player_hand)
    dealer_value = calculate_hand_value(dealer_hand)  # 此时庄家只有一张牌

    # 欧式规则：游戏开始时不检查庄家Blackjack，因为庄家只有一张牌。
    message = None
    message_class = ""

    session['game_state'] = {
        'deck': deck,
        'dealer_hand': dealer_hand,
        'player_hand': player_hand,
        'dealer_value': dealer_value,
        'player_value': player_value,
        'message': message,
        'message_class': message_class,
    }
    # Flask automatically marks the session as modified when you assign
    # a value to a session key. No need for `session.modified = True`.


def game_update(session, action):
    game_state = session.get('game_state', {})
    if not game_state:
        return new_game(session)

    session_id = session.get('session_id', '')
    deck = game_state['deck']
    dealer_hand = game_state['dealer_hand']
    player_hand = game_state['player_hand']

    if action == 'hit':
        # Deal a card to the player
        card = deck.pop()
        player_hand.append(card)
        player_value = calculate_hand_value(player_hand)
        game_state['player_value'] = player_value
        # add_log_entry(session_id, f'Player hits and gets {card}.')

        # Check if player busts
        if player_value > 21:
            # 玩家爆牌，游戏结束。此时庄家不需要再抽牌。
            game_state['dealer_value'] = calculate_hand_value(dealer_hand)
            game_state['message'] = 'You busted! Dealer wins.'
            game_state['message_class'] = 'lose-message'
            # add_log_entry(session_id, 'Player busts and loses.')
    elif action == 'stand':
        # ====== 欧式规则核心逻辑开始 ======
        # 1. 玩家停牌后，庄家才抽取第二张牌。
        card4 = deck.pop()
        dealer_hand.append(card4)
        
        # 2. 立即检查庄家是否构成“自然 Blackjack” (A + 10/J/Q/K)
        dealer_has_natural = is_natural_blackjack(dealer_hand)
        player_has_natural = is_natural_blackjack(player_hand)
        
        if dealer_has_natural:
            # 庄家有自然Blackjack
            game_state['dealer_value'] = 21
            if player_has_natural:
                # 玩家也有自然Blackjack -> 平局
                game_state['message'] = "It's a tie of double blackjack!"
                game_state['message_class'] = "tie-message"
                # add_log_entry(session_id, 'Dealer and player tie with both initial blackjack.')
            else:
                # 玩家没有自然Blackjack -> 庄家胜
                game_state['message'] = "Dealer wins with a natural Blackjack!"
                game_state['message_class'] = "lose-message"
                # add_log_entry(session_id, 'Dealer wins with an initial blackjack.')
        else:
            # 3. 如果庄家没有自然Blackjack，则按常规流程进行
            player_value = game_state['player_value']
            dealer_value = calculate_hand_value(dealer_hand)
            # add_log_entry(session_id, 'Player stands. ')
            while dealer_value < 17:
                card = deck.pop()
                dealer_hand.append(card)
                dealer_value = calculate_hand_value(dealer_hand)
                # add_log_entry(session_id, f'Dealer gets {card}.')

            game_state['dealer_value'] = dealer_value

            # Determine the winner (常规胜负判定)
            if dealer_value > 21:
                game_state['message'] = 'Dealer busted! You win!'
                game_state['message_class'] = 'win-message'
                # add_log_entry(session_id, 'Dealer busts. Player wins.')
            elif dealer_value > player_value:
                game_state['message'] = 'Dealer wins!'
                game_state['message_class'] = 'lose-message'
                # add_log_entry(session_id, f'Dealer wins by {dealer_value}:{player_value}.')
            elif dealer_value < player_value:
                game_state['message'] = 'You win!'
                game_state['message_class'] = 'win-message'
                # add_log_entry(session_id, f'Player wins by {player_value}:{dealer_value}.')
            else:
                game_state['message'] = "It's a tie!"
                game_state['message_class'] = 'tie-message'
                # add_log_entry(session_id, f'Dealer and Player tie with {player_value}:{dealer_value}.')
        # ====== 欧式规则核心逻辑结束 ======
    else:
        # add_log_entry(session_id, f'Unknown action {action}.')
        return

    # game state has changed itself so tell session it has changed
    session.modified = True
