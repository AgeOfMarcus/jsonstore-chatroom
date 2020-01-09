import json_store_client, hashlib, _thread, time, argparse
from output import color, Notifier, msg as log

class RestrictedUsernameError(BaseException):
	pass
class UsernameTakenError(BaseException):
	pass

class Client(object):
	def __init__(self, chatroom, username):
		# checking
		if username == "users":
			raise RestrictedUsernameError("Username cannot be 'users'")

		self.client = json_store_client.Client((
			hashlib.sha256(
				(chatroom+"jschat").encode()).hexdigest()*64)[:64])
		self.user = username
		self._join_chatroom()

	def _join_chatroom(self):
		users = self.client.retrieve("users") or []
		if self.user in users:
			raise UsernameTakenError("Change your username and try again")
		users.append(self.user)
		self.client.store("users", users)
		while not self.user in self.client.retrieve("users"):
			self._join_chatroom()
	def _get_messages(self):
		res = {}
		users = self.client.retrieve("users")
		for user in users:
			res[user] = self.client.retrieve(user) or []
		return res
	def _combine_messages(self, m):
		msgs = []
		for user, msglist in m.items():
			for msg in msglist:
				msg['user'] = user
				msgs.append(msg)
		return msgs
	def _sort_messages(self, msgs):
		msgt = {}
		for msg in msgs:
			while msg['time'] in msgt:
				msg['time'] += 0.000000001
			msgt[msg['time']] = msg
		sort = sorted(msgt)
		msgs = []
		for ts in sort:
			msgs.append(msgt[ts])
		return msgs

	def get_messages(self):
		return self._sort_messages(self._combine_messages(self._get_messages()))
	def send(self, msg):
		m = {'time':time.time(), 'msg':msg}
		old = self.client.retrieve(self.user) or []
		old.append(m)
		self.client.store(self.user, old)
	def exit(self):
		old = self.client.retrieve("users") or []
		if not self.user in old:
			return
		while self.user in old:
			old.remove(self.user)
			self.client.store("users",old)
			old = self.client.retrieve("users") or []


class TUI(object):
	def __init__(self, client, prompt="SEND: "):
		self.client = client
		self.notifier = Notifier(prompt)
		self.man = {
		"help":"show the help menu",
		"help $cmd":"show help for a command",
		"exit":"exit the chat",
		"online":"show who is online",
		}

	def format_msg(self, msg):
		return "<%s> %s" % (
			color.GREEN + msg['user'] + color.END,
			msg['msg'])
	def msg_checker(self):
		old = self.client.get_messages()
		[self.notifier.messages.append(self.format_msg(m)) for m in old]
		while True:
			new = self.client.get_messages()
			for i in new:
				if not i in old:
					self.notifier.messages.append(self.format_msg(i))
					old.append(i)
	def show_help(self, c=None):
		if c is None:
			for c in self.man:
				print(color.CYAN+c+color.END+": "+self.man[c])
		else:
			print(color.CYAN+c+color.END+": "+self.man[c]) if c in man else print(log.alert("Invalid command"))
	def handle_command(self, cmd):
		com = cmd.split(" ")
		if com[0] == "help":
			if len(com) > 1:
				self.show_help(com[1])
			else:
				self.show_help()
		elif com[0] == "exit":
			self.client.exit()
			exit(0)
		elif com[0] == "online":
			users = self.client.client.retrieve("users")
			print(log.info("Online: "+', '.join(users)))
		else:
			print(log.alert("Invalid command"))
	def start(self):
		_thread.start_new_thread(self.msg_checker, ())
		self.notifier.start()
		while True:
			msg = input("SEND: ")
			if msg.startswith("/"):
				self.handle_command(msg[1:])
			else:
				self.client.send(msg)


def parse_args():
	p = argparse.ArgumentParser()
	p.add_argument(
		"-c","--chatroom",
		help=("Name of chatroom to connect to"),
		required=True)
	p.add_argument(
		"-u","--username",
		help=("Username to display"),
		required=True)
	return p.parse_args()
def main(args):
	print(log.plus("Connecting... Type /help for commands"))
	ui = TUI(Client(args.chatroom, args.username))
	ui.start()
main(parse_args()) if __name__ == "__main__" else None