import os
from ddpg import DDPG
import gym
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


class MountainCar():

    def __init__(self):
        self.env = self.new_env()
        self.agent = DDPG()

    def new_env(self):
        return gym.make('MountainCarContinuous-v0')

    def preprocess_state(self, state):
        # mapping the state values to [-1,1]
        s = np.array(state)
        s[0] = ((state[0] + 1.2) / 1.8) * 2 - 1
        s[1] = ((state[1] + 0.07) / 0.14) * 2 - 1
        return s

    def plot_Q(self):
        """
        Plots 4 heatmaps that shows the behavior of the
        local critic and target when dealing with the state
        and actions space
        """
        state_step = 0.1
        action_step = 0.1
        plot_range = np.arange(-1, 1 + state_step, state_step)
        action_range = np.arange(-1, 1 + action_step, action_step)
        shape = plot_range.shape[0]
        matrix_Q = np.zeros((shape, shape))
        matrix_mQ = np.zeros((shape, shape))
        matrix_sQ = np.zeros((shape, shape))
        matrix_A = np.zeros((shape, shape))
        for i in range(shape):
            for j in range(shape):
                pos = plot_range[j]
                vel = plot_range[i]
                state = np.array([pos, vel]).reshape(-1, 2)
                Q_list = []
                for a in action_range:
                    action = np.array(a).reshape(-1, 1)
                    Q_list.append(
                        self.agent.critic_local.model.predict([state, action]))
                matrix_Q[i][j] = np.max(Q_list)
                matrix_sQ[i][j] = np.std(Q_list)
                matrix_mQ[i][j] = action_range[np.argmax(Q_list)]
                matrix_A[i][j] = self.agent.actor_local.model.predict(state)
        extent = [plot_range[0], plot_range[-1], plot_range[0], plot_range[-1]]

        fig, ax = plt.subplots(2, 2, sharex=True)
        ax[0, 0].set_title('Q value max')
        ax[0, 0].set_ylabel('Velocity')
        ax[0, 0].set_xlabel('Position')
        divider = make_axes_locatable(ax[0, 0])
        cax = divider.append_axes('right', size='5%', pad=0.05)
        im = ax[0, 0].imshow(matrix_Q, extent=extent, origin='lower')
        plt.colorbar(im, cax=cax)

        ax[0, 1].set_title('Q value std')
        ax[0, 1].set_ylabel('Velocity')
        ax[0, 1].set_xlabel('Position')
        divider = make_axes_locatable(ax[0, 1])
        cax = divider.append_axes('right', size='5%', pad=0.05)
        im = ax[0, 1].imshow(matrix_sQ, extent=extent, origin='lower')
        plt.colorbar(im, cax=cax)

        ax[1, 0].set_title('Action with Q max')
        ax[1, 0].set_ylabel('Velocity')
        ax[1, 0].set_xlabel('Position')
        divider = make_axes_locatable(ax[1, 0])
        cax = divider.append_axes('right', size='5%', pad=0.05)
        im = ax[1, 0].imshow(matrix_mQ, extent=extent, origin='lower')
        plt.colorbar(im, cax=cax)

        ax[1, 1].set_title('Predicted Action')
        ax[1, 1].set_ylabel('Velocity')
        ax[1, 1].set_xlabel('Position')
        divider = make_axes_locatable(ax[1, 1])
        cax = divider.append_axes('right', size='5%', pad=0.05)
        im = ax[1, 1].imshow(matrix_A, extent=extent, origin='lower')
        plt.colorbar(im, cax=cax)

        plt.subplots_adjust(top=0.92, right=0.95, hspace=0.25, wspace=0.4)

        plt.show()

    def run_epoch(self, render=False, training=True):
        state = self.preprocess_state(self.env.reset())
        self.agent.reset_episode(state)
        actions_list = []
        total_reward = 0
        steps = 0
        done = False
        while not done:
            steps += 1
            noisy_action, pure_action = self.agent.act(state)

            # use action with OUNoise if training
            action = noisy_action if training else pure_action

            # step into the environment and update values
            next_state, reward, done, info = self.env.step(action)
            next_state = self.preprocess_state(next_state)
            state = next_state
            total_reward += reward
            actions_list.append(pure_action)

            # only train agent if in training
            if training:
                self.agent.step(action, reward, next_state, done)

            if render:
                self.env.render()

            if done:
                if render:  # workaround render errors
                    self.env.close()
                    self.env = self.new_env()
                break

        action_mean = np.mean(actions_list)
        action_std = np.std(actions_list)

        return total_reward, done, action_mean, action_std, steps

    def run_model(self, max_epochs=100, n_solved=1, r_solved=90, plot_Q=False):
        """
        Train the learner

        Params
            ======
                max_epochs (int): Maximum number of training episodes
                r_solved (int): Minimum reward value to consider episode solved
                n_solved (int): Targed number of solved episodes before break
                plot_Q (bool): If true will plot state action values heatmaps
        """

        solved = False
        train_hist = []
        test_hist = []

        for epoch in range(1, max_epochs+1):
            (train_reward, train_done, train_action_mean, train_action_std,
             train_steps) = self.run_epoch()
            (test_reward, test_done, test_action_mean, test_action_std,
             test_steps) = self.run_epoch(training=False)

            train_hist.append([train_reward, train_steps])
            test_hist.append([test_reward, test_steps])

            # check if solved
            # if the mean of last n_solved teste episodes are
            # greater than r_solved, it is solved!

            if epoch > n_solved:
                train_running = np.mean([r for r, s in train_hist][-n_solved:])
                test_running = np.mean([r for r, s in test_hist][-n_solved:])
            else:
                train_running = np.mean([r for r, s in train_hist])
                test_running = np.mean([r for r, s in test_hist])

            print('Epoch:{:4}\n'
                  'Train: reward:{:6.1f}\tsteps:{:6.0f}\t'
                  'hist:{:6.1f}\taction/std:{:.3f}/{:.3f}\n'
                  'Test:  reward:{:6.1f}\tsteps:{:6.0f}\t'
                  'hist:{:6.1f}\taction/std:{:.3f}/{:.3f}\n'
                  .format(epoch, train_reward, train_steps,
                          train_running, train_action_mean, train_action_std,
                          test_reward, test_steps, test_running,
                          test_action_mean, test_action_std))

            if test_running > r_solved and epoch > n_solved:
                print('\nSolved! Average of {:4.1f} from episode {} to {}'
                      .format(test_running, epoch - n_solved + 1, epoch))
                solved = epoch
                break

        if plot_Q:
            self.plot_Q()
        return train_hist, test_hist, solved


if __name__ == '__main__':
    learner = MountainCar()
    learner.run_model(max_epochs=10, n_solved=3, plot_Q=True)
