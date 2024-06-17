from ai.util import Content, Target

def predict(model: str, content: Content, target: Target) -> float:
    if model=="ashokkumar2024":
        from ai.ashokkumar2024.model import predict as predict_ashokkumar2024
        return predict_ashokkumar2024(content, target)
    
    elif model=="basic":
        from ai.basic.model import predict as predict_basic
        return predict_basic(content, target)

    else:
        raise NotImplementedError()