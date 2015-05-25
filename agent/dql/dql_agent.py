import logging
import pickle
import random

from .states_memory import TransitionTable
from .nnet import NeuralNet


logger = logging.getLogger('keepaway')


class DQLAgent(object):
    # number of most recent transitions (s, a, r, s') in history
    transitions_history_size = 10**6
    # minibatch size
    minibatch_size = 2
    # number of most recent states that are given as input to network
    recent_states_to_network = 1
    # discount factor
    discount_factor = 0.99
    # learning rare
    learning_rate = 0.00025
    # epsilon-greedy factors
    initial_epsilon_greedy = 1  # every action is random action
    final_epsilon_greedy = 0.05  # one for 20 actions is random
    exploration_time = float(10**6)  # number of episodes over which epsilon factor is linearly annealed to it's final value
    # start learn after X episodes
    start_learn_after = 10**2
    # network architecture (first layer is number of inputs, last is number of actions)
    network_architecture = [13, 30, 30, 3]
    # possible number of actions
    number_of_actions = 3
    # state size
    state_size = 13
    # if training mode
    train = True
    # hardcoded epsilon for tests
    evaluation_epsilon = 0.05

    @property
    def epsilon(self):
        if not self.train:
            return self.evaluation_epsilon
        return min(
            max(
                self.initial_epsilon_greedy - (self.episodes_played - self.start_learn_after) / self.exploration_time,
                self.final_epsilon_greedy
            ),
            1
        )

    def __init__(self, **kwargs):
        for kw_name, kw_val in kwargs.iteritems():
            setattr(self, kw_name, kw_val)
        self.number_of_actions = self.network_architecture[-1]

        self.memory = TransitionTable(
            self.transitions_history_size,
            state_size=self.state_size,
            full_state_samples_count=self.recent_states_to_network,
        )
        self.nnet = NeuralNet(
            n_inputs=self.state_size,
            architecture=self.network_architecture,
            discount_factor=self.discount_factor,
            learning_rate=self.learning_rate
        )
        self.episodes_played = 0
        self.scores = []
        # self._init_new_game()
        logger.warning(str(self))
        self._episode_started = False
        self.last_state = None
        self.last_action = None
        self._last_time = 0
        self.current_game_total_reward = 0

    def __str__(self):
        result = ['DQL config:']
        for v in [
            'transitions_history_size', 'minibatch_size',
            'recent_states_to_network', 'discount_factor', 'learning_rate',
            'initial_epsilon_greedy', 'final_epsilon_greedy',
            'exploration_time', 'start_learn_after', 'network_architecture',
            'number_of_actions', 'state_size', 'train'
        ]:
            result.append('{}: {}'.format(v, getattr(self, v)))
        return '\n'.join(result)

    def _init_new_game(self):
        logger.debug('initializing new game (episode)')
        logger.debug('episodes played so far: {}'.format(self.episodes_played))
        self.last_state = None
        self.last_action = None
        self.current_game_total_reward = 0
        self._episode_started = True
        self.episodes_played += 1
        # self.memory.add(np.zeros((self.state_size,)), 0, 0, False)

    def _train_minibatch(self):
        logger.debug('Training minibatch of size {}'.format(self.minibatch_size))
        minibatch = self.memory.get_minibatch(self.minibatch_size)
        logger.debug('Minibatch (prestates, actions, rewards, poststates, terminals):\n {}'.format(minibatch))
        self.nnet.train_minibatch(minibatch)

    def _remember_in_memory(self, reward, is_terminal=False):
        """
        Save in memory last state, last action done, reward and information
        if after making last action there was a terminal state.
        """
        logger.debug('Rembemering last state in memory with reward {} (is_terminal: {})'.format(reward, is_terminal))
        self.memory.add(
            self.last_state, self.last_action, max(reward, 0), is_terminal
        )
        self.current_game_total_reward += reward

    def _get_next_action(self):
        """
        Return next action to be done.
        """
        current_state = self.memory.get_last_full_state()
        logger.debug('current epsilon: {}'.format(self.epsilon))
        if random.uniform(0, 1) < self.epsilon or self.episodes_played < self.start_learn_after:
            logger.debug('returning random action')
            action = random.choice(range(self.number_of_actions))
        else:
            logger.debug('predicting action by nnet')
            action = self.nnet.predict_best_action(current_state)
        self.last_action = action
        # self.frames_played += 1
        return action

    def _get_network_dump(self):
        return pickle.dumps(self.nnet.params_raw)

    # ==================================

    def start_episode(self, current_time, *args, **kwargs):
        logger.debug('starting new episode')
        if not self._episode_started:
            self._init_new_game()
            logger.debug('starting episode; current time: {}'.format(current_time))
            self._last_time = current_time
        return self.step(current_time=current_time, *args, **kwargs)

    def step(self, current_time, current_state, *args, **kwargs):
        logger.debug('step')
        if self.last_state is not None:
            self._remember_in_memory(current_time - self._last_time)
        if self.train and self.episodes_played > self.start_learn_after:
            self._train_minibatch()
        self.last_action = self._get_next_action()
        self.last_state = current_state
        self._last_time = current_time
        logger.info('Best action: {}'.format(self.last_action))
        return self.last_action

    def end_episode(self, current_time, *args, **kwargs):
        logger.debug('episode end')
        if self._episode_started:
            if self.last_state is not None:
                self._remember_in_memory(current_time - self._last_time, True)
            self.scores.append(self.current_game_total_reward)
            self._episode_started = False