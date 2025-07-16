import unittest
import asyncio

from microenv import microenv


class TestMicroEnv(unittest.TestCase):
    def setUp(self):
        # Sample data and descriptor
        self.data = {"public": 1, "secret": "top-secret"}
        self.descriptor = {
            "children": [
                {"key": "public", "type": "number"},
                {"key": "secret", "type": "string", "private": True},
            ]
        }
        # Create env and its event loop
        self.env = microenv(obj=self.data.copy(), descriptor=self.descriptor)
        self.face = self.env.face
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_basic_get_set_face(self):
        # face access with no caller
        self.assertEqual(self.face.public, 1)
        # face setattr
        self.face.public = 5
        self.assertEqual(self.face.public, 5)
        self.assertEqual(self.env.data["public"], 5)

    def test_privacy_enforcement_get(self):
        # get with caller on a private key should raise
        with self.assertRaises(KeyError):
            _ = self.env.get("secret", caller="user")
        # direct face read bypasses privacy
        self.assertEqual(self.face.secret, "top-secret")

    def test_privacy_enforcement_set(self):
        # set with caller on a private key should raise
        with self.assertRaises(KeyError):
            self.env.set("secret", "exposed!", caller="user")
        # direct face write bypasses privacy
        self.face.secret = "exposed!"
        self.assertEqual(self.face.secret, "exposed!")
        self.assertEqual(self.env.data["secret"], "exposed!")

    def test_nonexistent_key_errors(self):
        # getattr on face should raise KeyError for missing key
        with self.assertRaises(KeyError):
            _ = self.face.nonexistent
        # setattr on face should raise KeyError for missing key
        with self.assertRaises(KeyError):
            self.face.nonexistent = 42
        # direct get on env
        with self.assertRaises(KeyError):
            self.env.get("nope")
        # direct set on env
        with self.assertRaises(KeyError):
            self.env.set("nope", 0)

    def test_nonprivate_set_with_caller(self):
        # setting a non-private key with a caller is allowed
        val = self.env.set("public", 99, caller="anyone")
        self.assertEqual(val, 99)
        self.assertEqual(self.env.data["public"], 99)

    def test_pending_get_before_next(self):
        # before any next_=True, get(caller) returns None
        self.assertEqual(self.env.get("public", caller="u"), 1)

    def test_await_next_value_single_subscriber(self):
        fut = self.env.get("public", caller="u", next_=True)

        self.assertIs(self.env.get("public", caller="u", next_=True), fut)
        self.env.set("public", 42)

        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 42)

    def test_multiple_next_subscribers_share_future(self):
        # two calls to next_ before set should get the same Future
        fut1 = self.env.get("public", caller="u", next_=True)
        fut2 = self.env.get("public", caller="u", next_=True)
        self.assertIs(fut1, fut2)
        # resolve
        self.env.set("public", 123)
        r = self.loop.run_until_complete(fut2)
        self.assertEqual(r, 123)

    def test_descriptor_inference_when_missing(self):
        # If no descriptor is provided, children are inferred from the obj
        obj = {"a": None, "b": "str", "c": 3.14, "d": True, "e": [1, 2], "f": {"x": 1}}
        env2 = microenv(obj=obj, descriptor=None)
        # Build a map of key→type
        inferred = {c["key"]: c["type"] for c in env2.descriptor["children"]}
        self.assertEqual(inferred["a"], "null")
        self.assertEqual(inferred["b"], "string")
        self.assertEqual(inferred["c"], "number")
        self.assertEqual(inferred["d"], "boolean")
        self.assertEqual(inferred["e"], "array")
        self.assertEqual(inferred["f"], "object")

    def test_descriptor_unenforced_type(self):
        # Descriptor types are not enforced at runtime
        # we can set a number into a string-typed field without error
        self.env.set("secret", 555, caller=None)
        self.assertEqual(self.face.secret, 555)

    def test_readme_example(self):
        # Based on README quickstart
        data = {"public": 1, "secret": "s3cr3t"}
        descriptor = {
            "children": [
                {"key": "public", "type": "number"},
                {"key": "secret", "type": "string", "private": True},
            ]
        }
        env = microenv(obj=data.copy(), descriptor=descriptor)
        face = env.face

        # Basic get / set via the face
        self.assertEqual(face.public, 1)
        face.public = 42
        self.assertEqual(env.data["public"], 42)

        # Privacy: direct .secret bypasses privacy checks on the face
        self.assertEqual(face.secret, "s3cr3t")
        face.secret = "new!"
        self.assertEqual(env.data["secret"], "new!")

        # Async “next” subscription: await the next update to 'public'
        async def waiter():
            fut = env.get("public", next_=True)
            return await fut

        task = self.loop.create_task(waiter())
        # schedule a change immediately
        self.loop.call_soon(lambda: setattr(face, "public", 99))
        result = self.loop.run_until_complete(task)
        self.assertEqual(result, 99)


if __name__ == "__main__":
    unittest.main()
