import unittest

from ronovo_portfolio_auth.security_questions import QUESTIONS

from casino.accounts import AccountError, Accounts
from Tests.helpers import SECURITY, AppTestCase, DatabaseTestCase, login

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
        token = login(self.accounts, "Ronovo", "hunter22")
        self.assertEqual(self.accounts.security_question("ronovo"), QUESTION)
        self.accounts.reset_password("Ronovo", "mister whiskers", "newpass1")
        self.assertIsNone(self.accounts.resolve(token))
        self.assertTrue(login(self.accounts, "Ronovo", "newpass1"))

    def test_wrong_answers_lock_resets(self):
        for _ in range(5):
            with self.assertRaises(AccountError):
                self.accounts.reset_password("Ronovo", "rex", "newpass1")
        with self.assertRaisesRegex(AccountError, "Too many"):
            self.accounts.reset_password("Ronovo", "mister whiskers", "newpass1")

    def test_an_unknown_username_says_there_is_no_such_account(self):
        with self.assertRaisesRegex(AccountError, "no account with that username"):
            self.accounts.security_question("ghost")
        with self.assertRaisesRegex(AccountError, "no account with that username"):
            self.accounts.reset_password("ghost", "anything", "newpass1")

    def test_a_blank_username_is_asked_for(self):
        with self.assertRaisesRegex(AccountError, "Enter your username"):
            self.accounts.security_question("   ")

    def test_portfolio_accounts_cannot_be_reset(self):
        self.accounts.portfolio_user("7", "player7")
        with self.assertRaisesRegex(AccountError, "logs in with the portfolio"):
            self.accounts.reset_password("player7", "", "newpass1")


class ApiTests(AppTestCase):
    def test_reset_through_the_api(self):
        self.assertEqual(self.call("POST", "reset-question", {"username": "Ronovo"}, token=None),
                         {"question": SECURITY[0]})
        reset = {"username": "Ronovo", "answer": "REX", "password": "newpass1"}
        self.assertEqual(self.call("POST", "reset-password", reset, token=None), {"reset": True})


if __name__ == "__main__":
    unittest.main()
