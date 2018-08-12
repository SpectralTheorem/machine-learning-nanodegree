from keras import layers, models, optimizers, initializers, regularizers
from keras import backend as K


class Actor:
    """Actor (Policy) Model."""

    def __init__(self, state_size, action_size, action_low, action_high):
        """Initialize parameters and build model.

        Args:
            state_size (int): Dimension of each state
            action_size (int): Dimension of each action
            action_low (array): Min value of each action dimension
            action_high (array): Max value of each action dimension
        """
        self.state_size = state_size
        self.action_size = action_size
        self.action_low = action_low
        self.action_high = action_high
        self.action_range = action_high - action_low

        # Initialize any other variables here

        self.build_model()

    def build_model(self):
        """Build an actor (policy) network that maps states -> actions."""
        # Define input layer (states)
        states = layers.Input(shape=(self.state_size,), name='states')

        # Add hidden layers
        net = layers.Dense(units=40, activation='relu')(states)
        net = layers.Dense(units=20, activation='relu')(net)

        # Add final output layer
        actions = layers.Dense(units=self.action_size, activation='tanh',
                               name='raw_actions')(net)

        # Scale [-1, 1] output for each action dimension to proper range
        actions = layers.Lambda(
            lambda x: ((x + 1) * self.action_range / 2) + self.action_low,
            name='actions')(actions)

        # Create Keras model
        self.model = models.Model(inputs=states, outputs=actions)

        # Define loss function using action value (Q value) gradients
        action_gradients = layers.Input(shape=(self.action_size,))
        loss = K.mean(-action_gradients * actions)

        # Define optimizer and training function
        optimizer = optimizers.Adam(lr=0.0001)
        updates_op = optimizer.get_updates(
            params=self.model.trainable_weights, loss=loss)
        self.train_fn = K.function(
            inputs=[self.model.input, action_gradients, K.learning_phase()],
            outputs=[],
            updates=updates_op)
