

def handle(service,cookies,headers,method):
    service.set_body("<h1>index</h1>")
    # service.redirect_after("https://www.youtube.com/",5)
    service.create_session("me")
    data = {
        "name":"value",
        "name2":"value2",
        1:{
            "name":"value"
        },
        2:{
            "name":"value",
            "test":{
                "names":["value","value2","value3","value4","value5",{
                    "name":"value",
                    "hi":"value",
                    "home":{
                        "name":"value"
                    }
                }],
                "name":"value"

            }
        }
    }
    service.serve_json(data)
    print(service.get_session())
    return service.send()