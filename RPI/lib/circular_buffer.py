from ucollections import deque

class CircularBuffer:
    def __init__(self, max_size):
        self.data = deque((), max_size, True)
        self.max_size = max_size

    def __len__(self):
        return len(self.data)

    def is_empty(self):
        return not bool(self.data)

    def append(self, item):
        if len(self.data) >= self.max_size:
            self.data.popleft()  
        self.data.append(item)

    def pop(self):
        if self.is_empty():
            return None
        return self.data.popleft()

    def clear(self):
        self.data = deque((), self.max_size, True)

    def pop_head(self):
        if self.is_empty():
            return None

        temp_queue = deque((), self.max_size, True)

        for _ in range(len(self.data)):
            val = self.data.popleft()
            temp_queue.append(val)

        first_item = temp_queue.popleft()

        self.data = temp_queue

        return first_item

