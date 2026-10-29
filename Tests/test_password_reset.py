import unittest

from casino.accounts import AccountError, Accounts
from casino.config import TABLES_DIR
from casino.games import load_games
from ronovo_portfolio_auth.security_questions import QUESTIONS
from casino.web.server import CasinoApp
from Tests.helpers import DatabaseTestCase

QUESTION = QUESTIONS[1]


class PasswordResetTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.accounts = Accounts(self.db)
        self.user = self.accounts.register("Ronovo", "hunter22", QUESTION, "  Mister  Whiskers ")

    def test_registering_needs_a_listed_question_and_an_answer(self):
        for question, answer in (("Favorite color?", "blue"), (QUESTION, ""), (QUESTION, "   "), (QUESTION, None),
                                 (QUESTION, "x" * 101)):
            with self.subTest(question=question, answer=answer), self.assertRaises(AccountError):
                self.accounts.register("Other", "hunter22", question, answer)

    def test_the_right_answer_sets_a_new_password_and_logs_out_everywhere(self):
        token = self.accounts.login("Ronovo", "hunter22")
        self.assertEqual(self.accounts.security_question("ronovo"), QUESTION)
        self.accounts.reset_password("Ronovo", "mister whiskers", "newpass1")
        self.assertIsNone(self.accounts.resolve(token))
        self.assertTrue(self.accounts.login("Ronovo", "newpass1"))

    def test_wrong_answers_lock_resets(self):
        for _ in range(5):
            with self.assertRaises(AccountError):
                self.accounts.reset_password("Ronovo", "rex", "newpass1")
        with self.assertRaisesRegex(AccountError, "Too many"):
            self.accounts.reset_password("Ronovo", "mister whiskers", "newpass1")

    def test_unknown_usernames_get_a_steady_stand_in_question(self):
        question = self.accounts.security_question("ghost")
        self.assertIn(question, QUESTIONS)
        self.assertEqual(self.accounts.security_question("ghost"), question)
        with self.assertRaises(AccountError):
            self.accounts.reset_password("ghost", "anything", "newpass1")

    def test_portfolio_accounts_cannot_be_reset(self):
        self.accounts.portfolio_user("7", "player7")
        with self.assertRaises(AccountError):
            self.accounts.reset_password("player7", "", "newpass1")


class ApiTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.app = CasinoApp(self.db, load_games(TABLES_DIR))

    def test_reset_through_the_api(self):
        body = {"username": "Ronovo", "password": "hunter22", "question": QUESTION, "answer": "rex"}
        self.app.dispatch("POST", "register", body, None)
        self.assertEqual(self.app.dispatch("POST", "reset-question", {"username": "Ronovo"}, None).body,
                         {"question": QUESTION})
        reset = {"username": "Ronovo", "answer": "REX", "password": "newpass1"}
        self.assertEqual(self.app.dispatch("POST", "reset-password", reset, None).body, {"reset": True})


if __name__ == "__main__":
    unittest.main()
