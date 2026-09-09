# Reading from the rabbitmq queue

The waveform-controller container will process messages on a rabbitmq queue that
are JSON representations of the Emap-Interchange message types
`WaveformMessage` and, imminently, `WaveformLowFreqMessage`.

As you can see from `test_controller.test_controller_callback`, the following actions are
expected in various error cases:

* **Bad data (eg. missing column)**: REJECT without requeue, because it's assumed the message will never work.
* **Postgress connection failed**: REJECT with requeue, because failure is assumed to be unrelated to the received message.
* **Patient has research opt-out set** REJECT without requeue
