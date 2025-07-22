import unittest
import asyncio

# Import your microenv factory
from microenv import microenv


class TestCustomGetSetAsync(unittest.TestCase):
    def setUp(self):
        # base data + descriptor
        self.data = {"public": 1}
        self.descriptor = {"children": [{"key": "public", "type": "number"}]}

        # override get: synchronous, just tags the key
        def custom_get(key, env_ref, caller=None, next_=False):
            return f"got-{key}"

        # override set: asynchronous, multiplies by 10 after a tiny delay
        async def custom_set(key, value, env_ref, caller=None):
            # simulate asynchronous work in uasyncio/asyncio
            await asyncio.sleep(1)
            return value * 10

        self.overrides = {"get": custom_get, "set": custom_set}

        # create the environment with overrides
        self.env = microenv(
            obj=self.data.copy(), descriptor=self.descriptor, overrides=self.overrides
        )
        self.face = self.env.face

        # new event loop for testing async
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_custom_get_does_not_mutate_data(self):
        # reading via face → custom_get
        self.assertEqual(self.face.public, "got-public")
        # direct env.get → custom_get as well
        self.assertEqual(self.env.get("public"), "got-public")
        # original data remains untouched
        self.assertEqual(self.env.data["public"], 1)

    def test_awaiter_chains_through_async_set(self):
        # subscribe to next update
        get_coro = self.env.get("public", None, next_=True)
        self.assertTrue(asyncio.iscoroutine(get_coro))

        # call set (returns coroutine)
        set_fut = self.env.set("public", 3)
        self.assertTrue(asyncio.isfuture(set_fut))

        # first, run the override-set coroutine itself
        set_result = self.loop.run_until_complete(set_fut)
        self.assertEqual(set_result, 30)

        final = self.loop.run_until_complete(get_coro)
        self.assertEqual(final, 30)

    def test_face_after_set_still_uses_custom_get(self):
        # after setting, face.public should still invoke custom_get
        _ = self.loop.run_until_complete(self.env.set("public", 4))
        self.assertEqual(self.face.public, "got-public")


if __name__ == "__main__":
    unittest.main()
