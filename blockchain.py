import hashlib
import json
from datetime import datetime, timezone

class Block:
    def __init__(self, index, transactions, previous_hash, nonce=0):
        self.index = index
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        encoded = json.dumps(data, sort_keys=True, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self):
        self.chain = [Block(0, {"type": "GENESIS"}, "0")]

    def add_block(self, transactions):
        previous = self.chain[-1]
        block = Block(len(self.chain), transactions, previous.hash)
        self.chain.append(block)
        return block

    def is_valid(self):
        errors = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                errors.append(f"Block {current.index}: hash mismatch.")

            if current.previous_hash != previous.hash:
                errors.append(
                    f"Block {current.index}: previous hash does not match Block {previous.index}."
                )

        return len(errors) == 0, errors

    def to_dict(self):
        return [block.to_dict() for block in self.chain]
