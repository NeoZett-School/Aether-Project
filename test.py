from dataclasses import dataclass
@dataclass(slots=True)
class User:
    name: str
    def say_hello(self):
        print(f"{self.name} says hello!")
user = User(name="Some User")
user.say_hello()