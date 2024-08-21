from controller import ServoController

controller = ServoController()

if __name__ == "__main__":
    controller.execute_instruction(90, 100, 3, "Test")
    controller.execute_instruction(180, 200, 3, "Test2")
    controller.execute_instruction(0, 300, 3, "Test3")
    print("Degrees: ")
    deg = controller.get_motor_degrees()
    print(deg)
    controller.shutdown()