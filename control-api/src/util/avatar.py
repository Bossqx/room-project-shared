
import re
import json
import logging
from typing import Dict, List, Any, Union
from .dbcontroller import DBController



class AvatarGenerator:
    """
    A class to generate avatar URLs based on user identifiers.
    Supports multiple avatar services and customization options.
    """

    def get_store_avatarname(self,avartar:str):
        db=DBController()
        sql=f"""SELECT 
            avatar,
            store,
            avatarName,
            titleImage,
            logo 
        FROM avatars WHERE avatar=%s"""
        params=(avartar,)
        results=db.get_specific_sql(sql,None,params)
        return results

    def get_store_avatar(self):
        db=DBController()
        sql="SELECT avatar,store,avatarName,titleImage,logo FROM avatars "
        results=db.get_specific_sql(sql)
        return results
   
      

    def get_avatar_lists(self,avatar:str):
        db=DBController()
        sql="SELECT avatar,store,avatarList FROM avatars WHERE avatar=%s"
        params=(avatar,)
        result=db.get_specific_sql(sql,None,params)[0]
      
        avatarList=result['avatarList']
        #return avatarList
        # # Parse comma-separated avatar list into array
        # # Format: "W01.jpg,W02.jpg\r\n\r\n" -> ["W01.jpg", "W02.jpg"]
        parsed_list = []
        if avatarList:
            # Split by comma and strip whitespace/newlines from each entry
            parsed_list = [item.strip() for item in avatarList.split(',') if item.strip()]
        
        for i in range(len(parsed_list)):
            parsed_list[i]=f"{result['store']}/{parsed_list[i]}"

        return parsed_list

        
        

    