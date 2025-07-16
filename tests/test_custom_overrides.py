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
        def custom_get(key, env_ref, caller):
            return f"got-{key}"

        # override set: asynchronous, multiplies by 10 after a tiny delay
        async def custom_set(key, value, env_ref, caller):
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

    def test_custom_set_returns_coroutine_and_stores_it(self):
        # calling set returns a coroutine (because custom_set is async)
        coro = self.env.set("public", 2)
        self.assertTrue(
            asyncio.iscoroutine(coro),
            "env.set must return the coroutine from custom_set",
        )

        # before awaiting, obj['public'] holds that coroutine object
        self.assertIs(self.env.data["public"], coro)

        # awaiting the coroutine yields the transformed value
        result = self.loop.run_until_complete(coro)
        self.assertEqual(result, 20)

    def test_awaiter_chains_through_async_set(self):
        # subscribe to next update
        fut = self.env.get("public", next_=True)
        self.assertFalse(fut.done())

        # call set (returns coroutine)
        set_coro = self.env.set("public", 3)
        self.assertTrue(asyncio.iscoroutine(set_coro))
        self.assertFalse(fut.done())

        # first, run the override-set coroutine itself
        set_result = self.loop.run_until_complete(set_coro)
        self.assertEqual(set_result, 30)
        self.assertTrue(fut.done())

        final = self.loop.run_until_complete(fut)
        self.assertEqual(final, 30)

    def test_face_after_set_still_uses_custom_get(self):
        # after setting, face.public should still invoke custom_get
        _ = self.loop.run_until_complete(self.env.set("public", 4))
        self.assertEqual(self.face.public, "got-public")


if __name__ == "__main__":
    unittest.main()
